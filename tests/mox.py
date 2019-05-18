#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Mox, an object-mocking framework for Python.

Mox works in the record-replay-verify paradigm.  When you first create
a mock object, it is in record mode.  You then programmatically set
the expected behavior of the mock object (what methods are to be
called on it, with what parameters, what they should return, and in
what order).

Once you have set up the expected mock behavior, you put it in replay
mode.  Now the mock responds to method calls just as you told it to.
If an unexpected method (or an expected method with unexpected
parameters) is called, then an exception will be raised.

Once you are done interacting with the mock, you need to verify that
all the expected interactions occured.  (Maybe your code exited
prematurely without calling some cleanup method!)  The verify phase
ensures that every expected method was called; otherwise, an exception
will be raised.

WARNING! Mock objects created by Mox are not thread-safe.  If you are
call a mock in multiple threads, it should be guarded by a mutex.

TODO(stevepm): Add the option to make mocks thread-safe!

Suggested usage / workflow:

  # Create Mox factory
  my_mox = Mox()

  # Create a mock data access object
  mock_dao = my_mox.CreateMock(DAOClass)

  # Set up expected behavior
  mock_dao.RetrievePersonWithIdentifier('1').AndReturn(person)
  mock_dao.DeletePerson(person)

  # Put mocks in replay mode
  my_mox.ReplayAll()

  # Inject mock object and run test
  controller.SetDao(mock_dao)
  controller.DeletePersonById('1')

  # Verify all methods were called as expected
  my_mox.VerifyAll()
"""

from collections import deque
import difflib
import inspect
import re
import types
import unittest

import stubout

class Error(AssertionError):
  """Base exception for this module."""

  pass


class ExpectedMethodCallsError(Error):
  """Raised when Verify() is called before all expected methods have been called
  """

  def __init__(self, expected_methods):
    """Init exception.

    Args:
      # expected_methods: A sequence of MockMethod objects that should have been
      #   called.
      expected_methods: [MockMethod]

    Raises:
      ValueError: if expected_methods contains no methods.
    """

    if not expected_methods:
      raise ValueError("There must be at least one expected method")
    Error.__init__(self)
    self._expected_methods = expected_methods

  def __str__(self):
    calls = "\n".join(["%3d.  %s" % (i, m)
                       for i, m in enumerate(self._expected_methods)])
    return "Verify: Expected methods never called:\n%s" % (calls,)


class UnexpectedMethodCallError(Error):
  """Raised when an unexpected method is called.

  This can occur if a method is called with incorrect parameters, or out of the
  specified order.
  """

  def __init__(self, unexpected_method, expected):
    """Init exception.

    Args:
      # unexpected_method: MockMethod that was called but was not at the head of
      #   the expected_method queue.
      # expected: MockMethod or UnorderedGroup the method should have
      #   been in.
      unexpected_method: MockMethod
      expected: MockMethod or UnorderedGroup
    """

    Error.__init__(self)
    if expected is None:
      self._str = "Unexpected method call %s" % (unexpected_method,)
    else:
      differ = difflib.Differ()
      diff = differ.compare(str(unexpected_method).splitlines(True),
                            str(expected).splitlines(True))
      self._str = ("Unexpected method call.  unexpected:-  expected:+\n%s"
                   % ("\n".join(diff),))

  def __str__(self):
    return self._str


class UnknownMethodCallError(Error):
  """Raised if an unknown method is requested of the mock object."""

  def __init__(self, unknown_method_name):
    """Init exception.

    Args:
      # unknown_method_name: Method call that is not part of the mocked class's
      #   public interface.
      unknown_method_name: str
    """

    Error.__init__(self)
    self._unknown_method_name = unknown_method_name

  def __str__(self):
    return "Method called is not a member of the object: %s" % \
      self._unknown_method_name


class PrivateAttributeError(Error):
  """
  Raised if a MockObject is passed a private additional attribute name.
  """

  def __init__(self, attr):
    Error.__init__(self)
    self._attr = attr

  def __str__(self):
    return ("Attribute '%s' is private and should not be available in a mock "
            "object." % attr)


class ExpectedMockCreationError(Error):
  """Raised if mocks should have been created by StubOutClassWithMocks."""

  def __init__(self, expected_mocks):
    """Init exception.

    Args:
      # expected_mocks: A sequence of MockObjects that should have been
      #   created

    Raises:
      ValueError: if expected_mocks contains no methods.
    """

    if not expected_mocks:
      raise ValueError("There must be at least one expected method")
    Error.__init__(self)
    self._expected_mocks = expected_mocks

  def __str__(self):
    mocks = "\n".join(["%3d.  %s" % (i, m)
                       for i, m in enumerate(self._expected_mocks)])
    return "Verify: Expected mocks never created:\n%s" % (mocks,)


class UnexpectedMockCreationError(Error):
  """Raised if too many mocks were created by StubOutClassWithMocks."""

  def __init__(self, instance, *params, **named_params):
    """Init exception.

    Args:
      # instance: the type of obejct that was created
      # params: parameters given during instantiation
      # named_params: named parameters given during instantiation
    """

    Error.__init__(self)
    self._instance = instance
    self._params = params
    self._named_params = named_params

  def __str__(self):
    args = ", ".join(["%s" % v for i, v in enumerate(self._params)])
    error = "Unexpected mock creation: %s(%s" % (self._instance, args)

    if self._named_params:
      error += ", " + ", ".join(["%s=%s" % (k, v) for k, v in
                                 self._named_params.iteritems()])

    error += ")"
    return error


class Mox(object):
  """Mox: a factory for creating mock objects."""

  # A list of types that should be stubbed out with MockObjects (as
  # opposed to MockAnythings).
  _USE_MOCK_OBJECT = [types.ClassType, types.FunctionType, types.InstanceType,
                      types.ModuleType, types.ObjectType, types.TypeType]

  # A list of types that may be stubbed out with a MockObjectFactory.
  _USE_MOCK_FACTORY = [types.ClassType, types.ObjectType, types.TypeType]

  def __init__(self):
    """Initialize a new Mox."""

    self._mock_objects = []
    self.stubs = stubout.StubOutForTesting()

  def CreateMock(self, class_to_mock, attrs={}):
    """Create a new mock object.

    Args:
      # class_to_mock: the class to be mocked
      class_to_mock: class
      attrs: dict of attribute names to values that will be set on the mock
        object.  Only public attributes may be set.

    Returns:
      MockObject that can be used as the class_to_mock would be.
    """
    new_mock = MockObject(class_to_mock, attrs=attrs)
    self._mock_objects.append(new_mock)
    return new_mock

  def CreateMockAnything(self, description=None):
    """Create a mock that will accept any method calls.

    This does not enforce an interface.

    Args:
      description: str. Optionally, a descriptive name for the mock object being
        created, for debugging output purposes.
    """
    new_mock = MockAnything(description=description)
    self._mock_objects.append(new_mock)
    return new_mock

  def ReplayAll(self):
    """Set all mock objects to replay mode."""

    for mock_obj in self._mock_objects:
      mock_obj._Replay()


  def VerifyAll(self):
    """Call verify on all mock objects created."""

    for mock_obj in self._mock_objects:
      mock_obj._Verify()

  def ResetAll(self):
    """Call reset on all mock objects.  This does not unset stubs."""

    for mock_obj in self._mock_objects:
      mock_obj._Reset()

  def StubOutWithMock(self, obj, attr_name, use_mock_anything=False):
    """Replace a method, attribute, etc. with a Mock.

    This will replace a class or module with a MockObject, and everything else
    (method, function, etc) with a MockAnything.  This can be overridden to
    always use a MockAnything by setting use_mock_anything to True.

    Args:
      obj: A Python object (class, module, instance, callable).
      attr_name: str.  The name of the attribute to replace with a mock.
      use_mock_anything: bool. True if a MockAnything should be used regardless
        of the type of attribute.
    """

    attr_to_replace = getattr(obj, attr_name)
    attr_type = type(attr_to_replace)

    if attr_type == MockAnything or attr_type == MockObject:
      raise TypeError('Cannot mock a MockAnything! Did you remember to '
                      'call UnsetStubs in your previous test?')

    if attr_type in self._USE_MOCK_OBJECT and not use_mock_anything:
      stub = self.CreateMock(attr_to_replace)
    else:
      stub = self.CreateMockAnything(description='Stub for %s' % attr_to_replace)

    self.stubs.Set(obj, attr_name, stub)

  def StubOutClassWithMocks(self, obj, attr_name):
    """Replace a class with a "mock factory" that will create mock objects.

    This is useful if the code-under-test directly instantiates
    dependencies.  Previously some boilder plate was necessary to
    create a mock that would act as a factory.  Using
    StubOutClassWithMocks, once you've stubbed out the class you may
    use the stubbed class as you would any other mock created by mox:
    during the record phase, new mock instances will be created, and
    during replay, the recorded mocks will be returned.

    In replay mode

    # Example using StubOutWithMock (the old, clunky way):

    mock1 = mox.CreateMock(my_import.FooClass)
    mock2 = mox.CreateMock(my_import.FooClass)
    foo_factory = mox.StubOutWithMock(my_import, 'FooClass',
                                      use_mock_anything=True)
    foo_factory(1, 2).AndReturn(mock1)
    foo_factory(9, 10).AndReturn(mock2)
    mox.ReplayAll()

    my_import.FooClass(1, 2)   # Returns mock1 again.
    my_import.FooClass(9, 10)  # Returns mock2 again.
    mox.VerifyAll()

    # Example using StubOutClassWithMocks:

    mox.StubOutClassWithMocks(my_import, 'FooClass')
    mock1 = my_import.FooClass(1, 2)   # Returns a new mock of FooClass
    mock2 = my_import.FooClass(9, 10)  # Returns another mock instance
    mox.ReplayAll()

    my_import.FooClass(1, 2)   # Returns mock1 again.
    my_import.FooClass(9, 10)  # Returns mock2 again.
    mox.VerifyAll()
    """
    attr_to_replace = getattr(obj, attr_name)
    attr_type = type(attr_to_replace)

    if attr_type == MockAnything or attr_type == MockObject:
      raise TypeError('Cannot mock a MockAnything! Did you remember to '
                      'call UnsetStubs in your previous test?')

    if attr_type not in self._USE_MOCK_FACTORY:
      raise TypeError('Given attr is not a Class.  Use StubOutWithMock.')

    factory = _MockObjectFactory(attr_to_replace, self)
    self._mock_objects.append(factory)
    self.stubs.Set(obj, attr_name, factory)

  def UnsetStubs(self):
    """Restore stubs to their original state."""

    self.stubs.UnsetAll()

def Replay(*args):
  """Put mocks into Replay mode.

  Args:
    # args is any number of mocks to put into replay mode.
  """

  for mock in args:
    mock._Replay()


def Verify(*args):
  """Verify mocks.

  Args:
    # args is any number of mocks to be verified.
  """

  for mock in args:
    mock._Verify()


def Reset(*args):
  """Reset mocks.

  Args:
    # args is any number of mocks to be reset.
  """

  for mock in args:
    mock._Reset()


class MockAnything:
  """A mock that can be used to mock anything.

  This is helpful for mocking classes that do not provide a public interface.
  """

  def __init__(self, description=None):
    """Initialize a new MockAnything.

    Args:
      description: str. Optionally, a descriptive name for the mock object being
        created, for debugging output purposes.
    """
    self._description = description
    self._Reset()

  def __str__(self):
    return "<MockAnything instance at %s>" % id(self)

  def __repr__(self):
    return '<MockAnything instance>'

  def __getattr__(self, method_name):
    """Intercept method calls on this object.

     A new MockMethod is returned that is aware of the MockAnything's
     state (record or replay).  The call will be recorded or replayed
     by the MockMethod's __call__.

    Args:
      # method name: the name of the method being called.
      method_name: str

    Returns:
      A new MockMethod aware of MockAnything's state (record or replay).
    """

    return self._CreateMockMethod(method_name)

  def _CreateMockMethod(self, method_name, method_to_mock=None):
    """Create a new mock method call and return it.

    Args:
      # method_name: the name of the method being called.
      # method_to_mock: The actual method being mocked, used for introspection.
      method_name: str
      method_to_mock: a method object

    Returns:
      A new MockMethod aware of MockAnything's state (record or replay).
    """

    return MockMethod(method_name, self._expected_calls_queue,
                      self._replay_mode, method_to_mock=method_to_mock,
                      description=self._description)

  def __nonzero__(self):
    """Return 1 for nonzero so the mock can be used as a conditional."""

    return 1

  def __eq__(self, rhs):
    """Provide custom logic to compare objects."""

    return (isinstance(rhs, MockAnything) and
            self._replay_mode == rhs._replay_mode and
            self._expected_calls_queue == rhs._expected_calls_queue)

  def __ne__(self, rhs):
    """Provide custom logic to compare objects."""

    return not self == rhs

  def _Replay(self):
    """Start replaying expected method calls."""

    self._replay_mode = True

  def _Verify(self):
    """Verify that all of the expected calls have been made.

    Raises:
      ExpectedMethodCallsError: if there are still more method calls in the
        expected queue.
    """

    # If the list of expected calls is not empty, raise an exception
    if self._expected_calls_queue:
      # The last MultipleTimesGroup is not popped from the queue.
      if (len(self._expected_calls_queue) == 1 and
          isinstance(self._expected_calls_queue[0], MultipleTimesGroup) and
          self._expected_calls_queue[0].IsSatisfied()):
        pass
      else:
        raise ExpectedMethodCallsError(self._expected_calls_queue)

  def _Reset(self):
    """Reset the state of this mock to record mode with an empty queue."""

    # Maintain a list of method calls we are expecting
    self._expected_calls_queue = deque()

    # Make sure we are in setup mode, not replay mode
    self._replay_mode = False


class MockObject(MockAnything, object):
  """A mock object that simulates the public/protected interface of a class."""

  def __init__(self, class_to_mock, attrs={}):
    """Initialize a mock object.

    This determines the methods and properties of the class and stores them.

    Args:
      # class_to_mock: class to be mocked
      class_to_mock: class
      attrs: dict of attribute names to values that will be set on the mock
        object.  Only public attributes may be set.

    Raises:
      PrivateAttributeError: if a supplied attribute is not public.
      ValueError: if an attribute would mask an existing method.
    """

    # This is used to hack around the mixin/inheritance of MockAnything, which
    # is not a proper object (it can be anything. :-)
    MockAnything.__dict__['__init__'](self)

    # Get a list of all the public and special methods we should mock.
    self._known_methods = set()
    self._known_vars = set()
    self._class_to_mock = class_to_mock
    try:
      self._description = class_to_mock.__name__
      # If class_to_mock is a mock itself, then we'll get an UnknownMethodCall
      # error here from the underlying call to __getattr__('__name__')
    except (UnknownMethodCallError, AttributeError):
      try:
        self._description = type(class_to_mock).__name__
      except AttributeError:
        pass

    for method in dir(class_to_mock):
      attr = getattr(class_to_mock, method)
      if callable(attr):
        self._known_methods.add(method)
      elif not (type(attr) is property):
        # treating properties as class vars makes little sense.
        self._known_vars.add(method)

    # Set additional attributes at instantiation time; this is quicker
    # than manually setting attributes that are normally created in
    # __init__.
    for attr, value in attrs.items():
      if attr.startswith("_"):
        raise PrivateAttributeError(attr)
      elif attr in self._known_methods:
        raise ValueError("'%s' is a method of '%s' objects." % (attr,
                                                                class_to_mock))
      else:
        setattr(self, attr, value)

  def __getattr__(self, name):
    """Intercept attribute request on this object.

    If the attribute is a public class variable, it will be returned and not
    recorded as a call.

    If the attribute is not a variable, it is handled like a method
    call. The method name is checked against the set of mockable
    methods, and a new MockMethod is returned that is aware of the
    MockObject's state (record or replay).  The call will be recorded
    or replayed by the MockMethod's __call__.

    Args:
      # name: the name of the attribute being requested.
      name: str

    Returns:
      Either a class variable or a new MockMethod that is aware of the state
      of the mock (record or replay).

    Raises:
      UnknownMethodCallError if the MockObject does not mock the requested
          method.
    """

    if name in self._known_vars:
      return getattr(self._class_to_mock, name)

    if name in self._known_methods:
      return self._CreateMockMethod(
          name,
          method_to_mock=getattr(self._class_to_mock, name))

    raise UnknownMethodCallError(name)

  def __eq__(self, rhs):
    """Provide custom logic to compare objects."""

    return (isinstance(rhs, MockObject) and
            self._class_to_mock == rhs._class_to_mock and
            self._replay_mode == rhs._replay_mode and
            self._expected_calls_queue == rhs._expected_calls_queue)

  def __setitem__(self, key, value):
    """Provide custom logic for mocking classes that support item assignment.

    Args:
      key: Key to set the value for.
      value: Value to set.

    Returns:
      Expected return value in replay mode.  A MockMethod object for the
      __setitem__ method that has already been called if not in replay mode.

    Raises:
      TypeError if the underlying class does not support item assignment.
      UnexpectedMethodCallError if the object does not expect the call to
        __setitem__.

    """
    # Verify the class supports item assignment.
    if '__setitem__' not in dir(self._class_to_mock):
      raise TypeError('object does not support item assignment')

    # If we are in replay mode then simply call the mock __setitem__ method.
    if self._replay_mode:
      return MockMethod('__setitem__', self._expected_calls_queue,
                        self._replay_mode)(key, value)


    # Otherwise, create a mock method __setitem__.
    return self._CreateMockMethod('__setitem__')(key, value)

  def __getitem__(self, key):
    """Provide custom logic for mocking classes that are subscriptable.

    Args:
      key: Key to return the value for.

    Returns:
      Expected return value in replay mode.  A MockMethod object for the
      __getitem__ method that has already been called if not in replay mode.

    Raises:
      TypeError if the underlying class is not subscriptable.
      UnexpectedMethodCallError if the object does not expect the call to
        __getitem__.

    """
    # Verify the class supports item assignment.
    if '__getitem__' not in dir(self._class_to_mock):
      raise TypeError('unsubscriptable object')

    # If we are in replay mode then simply call the mock __getitem__ method.
    if self._replay_mode:
      return MockMethod('__getitem__', self._expected_calls_queue,
                        self._replay_mode)(key)


    # Otherwise, create a mock method __getitem__.
    return self._CreateMockMethod('__getitem__')(key)

  def __iter__(self):
    """Provide custom logic for mocking classes that are iterable.

    Returns:
      Expected return value in replay mode.  A MockMethod object for the
      __iter__ method that has already been called if not in replay mode.

    Raises:
      TypeError if the underlying class is not iterable.
      UnexpectedMethodCallError if the object does not expect the call to
        __iter__.

    """
    methods = dir(self._class_to_mock)

    # Verify the class supports iteration.
    if '__iter__' not in methods:
      # If it doesn't have iter method and we are in replay method, then try to
      # iterate using subscripts.
      if '__getitem__' not in methods or not self._replay_mode:
        raise TypeError('not iterable object')
      else:
        results = []
        index = 0
        try:
          while True:
            results.append(self[index])
            index += 1
        except IndexError:
          return iter(results)

    # If we are in replay mode then simply call the mock __iter__ method.
    if self._replay_mode:
      return MockMethod('__iter__', self._expected_calls_queue,
                        self._replay_mode)()


    # Otherwise, create a mock method __iter__.
    return self._CreateMockMethod('__iter__')()


  def __contains__(self, key):
    """Provide custom logic for mocking classes that contain items.

    Args:
      key: Key to look in container for.

    Returns:
      Expected return value in replay mode.  A MockMethod object for the
      __contains__ method that has already been called if not in replay mode.

    Raises:
      TypeError if the underlying class does not implement __contains__
      UnexpectedMethodCaller if the object does not expect the call to
      __contains__.

    """
    contains = self._class_to_mock.__dict__.get('__contains__', None)

    if contains is None:
      raise TypeError('unsubscriptable object')

    if self._replay_mode:
      return MockMethod('__contains__', self._expected_calls_queue,
                        self._replay_mode)(key)

    return self._CreateMockMethod('__contains__')(key)

  def __call__(self, *params, **named_params):
    """Provide custom logic for mocking classes that are callable."""

    # Verify the class we are mocking is callable.
    callable = hasattr(self._class_to_mock, '__call__')
    if not callable:
      raise TypeError('Not callable')

    # Because the call is happening directly on this object instead of a method,
    # the call on the mock method is made right here

    # If we are mocking a Function, then use the function, and not the
    # __call__ method
    method = None
    if type(self._class_to_mock) == types.FunctionType:
      method = self._class_to_mock;
    else:
      method = getattr(self._class_to_mock, '__call__')
    mock_method = self._CreateMockMethod('__call__', method_to_mock=method)

    return mock_method(*params, **named_params)

  @property
  def __class__(self):
    """Return the class that is being mocked."""

    return self._class_to_mock


class _MockObjectFactory(MockObject):
  """A MockObjectFactory creates mocks and verifies __init__ params.

  A MockObjectFactory removes the boiler plate code that was previously
  necessary to stub out direction instantiation of a class.

  The MockObjectFactory creates new MockObjects when called and verifies the
  __init__ params are correct when in record mode.  When replaying, existing
  mocks are returned, and the __init__ params are verified.

  See StubOutWithMock vs StubOutClassWithMocks for more detail.
  """

  def __init__(self, class_to_mock, mox_instance):
    MockObject.__init__(self, class_to_mock)
    self._mox = mox_instance
    self._instance_queue = deque()

  def __call__(self, *params, **named_params):
    """Instantiate and record that a new mock has been created."""

    method = getattr(self._class_to_mock, '__init__')
    mock_method = self._CreateMockMethod('__init__', method_to_mock=method)
    # Note: calling mock_method() is deferred in order to catch the
    # empty instance_queue first.

    if self._replay_mode:
      if not self._instance_queue:
        raise UnexpectedMockCreationError(self._class_to_mock, *params,
                                          **named_params)

      mock_method(*params, **named_params)

      return self._instance_queue.pop()
    else:
      mock_method(*params, **named_params)

      instance = self._mox.CreateMock(self._class_to_mock)
      self._instance_queue.appendleft(instance)
      return instance

  def _Verify(self):
    """Verify that all mocks have been created."""
    if self._instance_queue:
      raise ExpectedMockCreationError(self._instance_queue)
    super(_MockObjectFactory, self)._Verify()


class MethodCallChecker(object):
  """Ensures that methods are called correctly."""

  _NEEDED, _DEFAULT, _GIVEN = range(3)

  def __init__(self, method):
    """Creates a checker.

    Args:
      # method: A method to check.
      method: function

    Raises:
      ValueError: method could not be inspected, so checks aren't possible.
        Some methods and functions like built-ins can't be inspected.
    """
    try:
      self._args, varargs, varkw, defaults = inspect.getargspec(method)
    except TypeError:
      raise ValueError('Could not get argument specification for %r'
                       % (method,))
    if inspect.ismethod(method):
      self._args = self._args[1:]  # Skip 'self'.
    self._method = method

    self._has_varargs = varargs is not None
    self._has_varkw = varkw is not None
    if defaults is None:
      self._required_args = self._args
      self._default_args = []
    else:
      self._required_args = self._args[:-len(defaults)]
      self._default_args = self._args[-len(defaults):]

  def _RecordArgumentGiven(self, arg_name, arg_status):
    """Mark an argument as being given.

    Args:
      # arg_name: The name of the argument to mark in arg_status.
      # arg_status: Maps argument names to one of _NEEDED, _DEFAULT, _GIVEN.
      arg_name: string
      arg_status: dict

    Raises:
      AttributeError: arg_name is already marked as _GIVEN.
    """
    if arg_status.get(arg_name, None) == MethodCallChecker._GIVEN:
      raise AttributeError('%s provided more than once' % (arg_name,))
    arg_status[arg_name] = MethodCallChecker._GIVEN

  def Check(self, params, named_params):
    """Ensures that the parameters used while recording a call are valid.

    Args:
      # params: A list of positional parameters.
      # named_params: A dict of named parameters.
      params: list
      named_params: dict

    Raises:
      AttributeError: the given parameters don't work with the given method.
    """
    arg_status = dict((a, MethodCallChecker._NEEDED)
                      for a in self._required_args)
    for arg in self._default_args:
      arg_status[arg] = MethodCallChecker._DEFAULT

    # Check that each positional param is valid.
    for i in range(len(params)):
      try:
        arg_name = self._args[i]
      except IndexError:
        if not self._has_varargs:
          raise AttributeError('%s does not take %d or more positional '
                               'arguments' % (self._method.__name__, i))
      else:
        self._RecordArgumentGiven(arg_name, arg_status)

    # Check each keyword argument.
    for arg_name in named_params:
      if arg_name not in arg_status and not self._has_varkw:
        raise AttributeError('%s is not expecting keyword argument %s'
                             % (self._method.__name__, arg_name))
      self._RecordArgumentGiven(arg_name, arg_status)

    # Ensure all the required arguments have been given.
    still_needed = [k for k, v in arg_status.iteritems()
                    if v == MethodCallChecker._NEEDED]
    if still_needed:
      raise AttributeError('No values given for arguments %s'
                           % (' '.join(sorted(still_needed))))


class MockMethod(object):
  """Callable mock method.

  A MockMethod should act exactly like the method it mocks, accepting parameters
  and returning a value, or throwing an exception (as specified).  When this
  method is called, it can optionally verify whether the called method (name and
  signature) matches the expected method.
  """

  def __init__(self, method_name, call_queue, replay_mode,
               method_to_mock=None, description=None):
    """Construct a new mock method.

    Args:
      # method_name: the name of the method
      # call_queue: deque of calls, verify this call against the head, or add
      #     this call to the queue.
      # replay_mode: False if we are recording, True if we are verifying calls
      #     against the call queue.
      # method_to_mock: The actual method being mocked, used for introspection.
      # description: optionally, a descriptive name for this method. Typically
      #     this is equal to the descriptive name of the method's class.
      method_name: str
      call_queue: list or deque
      replay_mode: bool
      method_to_mock: a method object
      description: str or None
    """

    self._name = method_name
    self.__name__ = method_name
    self._call_queue = call_queue
    if not isinstance(call_queue, deque):
      self._call_queue = deque(self._call_queue)
    self._replay_mode = replay_mode
    self._description = description

    self._params = None
    self._named_params = None
    self._return_value = None
    self._exception = None
    self._side_effects = None

    try:
      self._checker = MethodCallChecker(method_to_mock)
    except ValueError:
      self._checker = None

  def __call__(self, *params, **named_params):
    """Log parameters and return the specified return value.

    If the Mock(Anything/Object) associated with this call is in record mode,
    this MockMethod will be pushed onto the expected call queue.  If the mock
    is in replay mode, this will pop a MockMethod off the top of the queue and
    verify this call is equal to the expected call.

    Raises:
      UnexpectedMethodCall if this call is supposed to match an expected method
        call and it does not.
    """

    self._params = params
    self._named_params = named_params

    if not self._replay_mode:
      if self._checker is not None:
        self._checker.Check(params, named_params)
      self._call_queue.append(self)
      return self

    expected_method = self._VerifyMethodCall()

    if expected_method._side_effects:
      result = expected_method._side_effects(*params, **named_params)
      if expected_method._return_value is None:
        expected_method._return_value = result

    if expected_method._exception:
      raise expected_method._exception

    return expected_method._return_value

  def __getattr__(self, name):
    """Raise an AttributeError with a helpful message."""

    raise AttributeError('MockMethod has no attribute "%s". '
        'Did you remember to put your mocks in replay mode?' % name)

  def __iter__(self):
    """Raise a TypeError with a helpful message."""
    raise TypeError('MockMethod cannot be iterated. '
                    'Did you remember to put your mocks in replay mode?')

  def next(self):
    """Raise a TypeError with a helpful message."""
    raise TypeError('MockMethod cannot be iterated. '
                    'Did you remember to put your mocks in replay mode?')

  def _PopNextMethod(self):
    """Pop the next method from our call queue."""
    try:
      return self._call_queue.popleft()
    except IndexError:
      raise UnexpectedMethodCallError(self, None)

  def _VerifyMethodCall(self):
    """Verify the called method is expected.

    This can be an ordered method, or part of an unordered set.

    Returns:
      The expected mock method.

    Raises:
      UnexpectedMethodCall if the method called was not expected.
    """

    expected = self._PopNextMethod()

    # Loop here, because we might have a MethodGroup followed by another
    # group.
    while isinstance(expected, MethodGroup):
      expected, method = expected.MethodCalled(self)
      if method is not None:
        return method

    # This is a mock method, so just check equality.
    if expected != self:
      raise UnexpectedMethodCallError(self, expected)

    return expected

  def __str__(self):
    params = ', '.join(
        [repr(p) for p in self._params or []] +
        ['%s=%r' % x for x in sorted((self._named_params or {}).items())])
    full_desc = "%s(%s) -> %r" % (self._name, params, self._return_value)
    if self._description:
      full_desc = "%s.%s" % (self._description, full_desc)
    return full_desc

  def __eq__(self, rhs):
    """Test whether this MockMethod is equivalent to another MockMethod.

    Args:
      # rhs: the right hand side of the test
      rhs: MockMethod
    """

    return (isinstance(rhs, MockMethod) and
            self._name == rhs._name and
            self._params == rhs._params and
            self._named_params == rhs._named_params)

  def __ne__(self, rhs):
    """Test whether this MockMethod is not equivalent to another MockMethod.

    Args:
      # rhs: the right hand side of the test
      rhs: MockMethod
    """

    return not self == rhs

  def GetPossibleGroup(self):
    """Returns a possible group from the end of the call queue or None if no
    other methods are on the stack.
    """

    # Remove this method from the tail of the queue so we can add it to a group.
    this_method = self._call_queue.pop()
    assert this_method == self

    # Determine if the tail of the queue is a group, or just a regular ordered
    # mock method.
    group = None
    try:
      group = self._call_queue[-1]
    except IndexError:
      pass

    return group

  def _CheckAndCreateNewGroup(self, group_name, group_class):
    """Checks if the last method (a possible group) is an instance of our
    group_class. Adds the current method to this group or creates a new one.

    Args:

      group_name: the name of the group.
      group_class: the class used to create instance of this new group
    """
    group = self.GetPossibleGroup()

    # If this is a group, and it is the correct group, add the method.
    if isinstance(group, group_class) and group.group_name() == group_name:
      group.AddMethod(self)
      return self

    # Create a new group and add the method.
    new_group = group_class(group_name)
    new_group.AddMethod(self)
    self._call_queue.append(new_group)
    return self

  def InAnyOrder(self, group_name="default"):
    """Move this method into a group of unordered calls.

    A group of unordered calls must be defined together, and must be executed
    in full before the next expected method can be called.  There can be
    multiple groups that are expected serially, if they are given
    different group names.  The same group name can be reused if there is a
    standard method call, or a group with a different name, spliced between
    usages.

    Args:
      group_name: the name of the unordered group.

    Returns:
      self
    """
    return self._CheckAndCreateNewGroup(group_name, UnorderedGroup)

  def MultipleTimes(self, group_name="default"):
    """Move this method into group of calls which may be called multiple times.

    A group of repeating calls must be defined together, and must be executed in
    full before the next expected mehtod can be called.

    Args:
      group_name: the name of the unordered group.

    Returns:
      self
    """
    return self._CheckAndCreateNewGroup(group_name, MultipleTimesGroup)

  def AndReturn(self, return_value):
    """Set the value to return when this method is called.

    Args:
      # return_value can be anything.
    """

    self._return_value = return_value
    return return_value

  def AndRaise(self, exception):
    """Set the exception to raise when this method is called.

    Args:
      # exception: the exception to raise when this method is called.
      exception: Exception
    """

    self._exception = exception

  def WithSideEffects(self, side_effects):
    """Set the side effects that are simulated when this method is called.

    Args:
      side_effects: A callable which modifies the parameters or other relevant
        state which a given test case depends on.

    Returns:
      Self for chaining with AndReturn and AndRaise.
    """
    self._side_effects = side_effects
    return self

class Comparator:
  """Base class for all Mox comparators.

  A Comparator can be used as a parameter to a mocked method when the exact
  value is not known.  For example, the code you are testing might build up a
  long SQL string that is passed to your mock DAO. You're only interested that
  the IN clause contains the proper primary keys, so you can set your mock
  up as follows:

  mock_dao.RunQuery(StrContains('IN (1, 2, 4, 5)')).AndReturn(mock_result)

  Now whatever query is passed in must contain the string 'IN (1, 2, 4, 5)'.

  A Comparator may replace one or more parameters, for example:
  # return at most 10 rows
  mock_dao.RunQuery(StrContains('SELECT'), 10)

  or

  # Return some non-deterministic number of rows
  mock_dao.RunQuery(StrContains('SELECT'), IsA(int))
  """

  def equals(self, rhs):
    """Special equals method that all comparators must implement.

    Args:
      rhs: any python object
    """

    raise NotImplementedError, 'method must be implemented by a subclass.'

  def __eq__(self, rhs):
    return self.equals(rhs)

  def __ne__(self, rhs):
    return not self.equals(rhs)


class IsA(Comparator):
  """This class wraps a basic Python type or class.  It is used to verify
  that a parameter is of the given type or class.

  Example:
  mock_dao.Connect(IsA(DbConnectInfo))
  """

  def __init__(self, class_name):
    """Initialize IsA

    Args:
      class_name: basic python type or a class
    """

    self._class_name = class_name

  def equals(self, rhs):
    """Check to see if the RHS is an instance of class_name.

    Args:
      # rhs: the right hand side of the test
      rhs: object

    Returns:
      bool
    """

    try:
      return isinstance(rhs, self._class_name)
    except TypeError:
      # Check raw types if there was a type error.  This is helpful for
      # things like cStringIO.StringIO.
      return type(rhs) == type(self._class_name)

  def __repr__(self):
    return str(self._class_name)

class IsAlmost(Comparator):
  """Comparison class used to check whether a parameter is nearly equal
  to a given value.  Generally useful for floating point numbers.

  Example mock_dao.SetTimeout((IsAlmost(3.9)))
  """

  def __init__(self, float_value, places=7):
    """Initialize IsAlmost.

    Args:
      float_value: The value for making the comparison.
      places: The number of decimal places to round to.
    """

    self._float_value = float_value
    self._places = places

  def equals(self, rhs):
    """Check to see if RHS is almost equal to float_value

    Args:
      rhs: the value to compare to float_value

    Returns:
      bool
    """

    try:
      return round(rhs-self._float_value, self._places) == 0
    except TypeError:
      # This is probably because either float_value or rhs is not a number.
      return False

  def __repr__(self):
    return str(self._float_value)

class StrContains(Comparator):
  """Comparison class used to check whether a substring exists in a
  string parameter.  This can be useful in mocking a database with SQL
  passed in as a string parameter, for example.

  Example:
  mock_dao.RunQuery(StrContains('IN (1, 2, 4, 5)')).AndReturn(mock_result)
  """

  def __init__(self, search_string):
    """Initialize.

    Args:
      # search_string: the string you are searching for
      search_string: str
    """

    self._search_string = search_string

  def equals(self, rhs):
    """Check to see if the search_string is contained in the rhs string.

    Args:
      # rhs: the right hand side of the test
      rhs: object

    Returns:
      bool
    """

    try:
      return rhs.find(self._search_string) > -1
    except Exception:
      return False

  def __repr__(self):
    return '<str containing \'%s\'>' % self._search_string


class Regex(Comparator):
  """Checks if a string matches a regular expression.

  This uses a given regular expression to determine equality.
  """

  def __init__(self, pattern, flags=0):
    """Initialize.

    Args:
      # pattern is the regular expression to search for
      pattern: str
      # flags passed to re.compile function as the second argument
      flags: int
    """

    self.regex = re.compile(pattern, flags=flags)

  def equals(self, rhs):
    """Check to see if rhs matches regular expression pattern.

    Returns:
      bool
    """

    return self.regex.search(rhs) is not None

  def __repr__(self):
    s = '<regular expression \'%s\'' % self.regex.pattern
    if self.regex.flags:
      s += ', flags=%d' % self.regex.flags
    s += '>'
    return s


class In(Comparator):
  """Checks whether an item (or key) is in a list (or dict) parameter.

  Example:
  mock_dao.GetUsersInfo(In('expectedUserName')).AndReturn(mock_result)
  """

  def __init__(self, key):
    """Initialize.

    Args:
      # key is any thing that could be in a list or a key in a dict
    """

    self._key = key

  def equals(self, rhs):
    """Check to see whether key is in rhs.

    Args:
      rhs: dict

    Returns:
      bool
    """

    return self._key in rhs

  def __repr__(self):
    return '<sequence or map containing \'%s\'>' % self._key


class Not(Comparator):
  """Checks whether a predicates is False.

  Example:
    mock_dao.UpdateUsers(Not(ContainsKeyValue('stevepm', stevepm_user_info)))
  """

  def __init__(self, predicate):
    """Initialize.

    Args:
      # predicate: a Comparator instance.
    """

    assert isinstance(predicate, Comparator), ("predicate %r must be a"
                                               " Comparator." % predicate)
    self._predicate = predicate

  def equals(self, rhs):
    """Check to see whether the predicate is False.

    Args:
      rhs: A value that will be given in argument of the predicate.

    Returns:
      bool
    """

    return not self._predicate.equals(rhs)

  def __repr__(self):
    return '<not \'%s\'>' % self._predicate


class ContainsKeyValue(Comparator):
  """Checks whether a key/value pair is in a dict parameter.

  Example:
  mock_dao.UpdateUsers(ContainsKeyValue('stevepm', stevepm_user_info))
  """

  def __init__(self, key, value):
    """Initialize.

    Args:
      # key: a key in a dict
      # value: the corresponding value
    """

    self._key = key
    self._value = value

  def equals(self, rhs):
    """Check whether the given key/value pair is in the rhs dict.

    Returns:
      bool
    """

    try:
      return rhs[self._key] == self._value
    except Exception:
      return False

  def __repr__(self):
    return '<map containing the entry \'%s: %s\'>' % (self._key, self._value)


class ContainsAttributeValue(Comparator):
  """Checks whether a passed parameter contains attributes with a given value.

  Example:
  mock_dao.UpdateSomething(ContainsAttribute('stevepm', stevepm_user_info))
  """

  def __init__(self, key, value):
    """Initialize.

    Args:
      # key: an attribute name of an object
      # value: the corresponding value
    """

    self._key = key
    self._value = value

  def equals(self, rhs):
    """Check whether the given attribute has a matching value in the rhs object.

    Returns:
      bool
    """

    try:
      return getattr(rhs, self._key) == self._value
    except Exception:
      return False


class SameElementsAs(Comparator):
  """Checks whether iterables contain the same elements (ignoring order).

  Example:
  mock_dao.ProcessUsers(SameElementsAs('stevepm', 'salomaki'))
  """

  def __init__(self, expected_seq):
    """Initialize.

    Args:
      expected_seq: a sequence
    """

    self._expected_seq = expected_seq

  def equals(self, actual_seq):
    """Check to see whether actual_seq has same elements as expected_seq.

    Args:
      actual_seq: sequence

    Returns:
      bool
    """

    try:
      expected = dict([(element, None) for element in self._expected_seq])
      actual = dict([(element, None) for element in actual_seq])
    except TypeError:
      # Fall back to slower list-compare if any of the objects are unhashable.
      expected = list(self._expected_seq)
      actual = list(actual_seq)
      expected.sort()
      actual.sort()
    return expected == actual

  def __repr__(self):
    return '<sequence with same elements as \'%s\'>' % self._expected_seq


class And(Comparator):
  """Evaluates one or more Comparators on RHS and returns an AND of the results.
  """

  def __init__(self, *args):
    """Initialize.

    Args:
      *args: One or more Comparator
    """

    self._comparators = args

  def equals(self, rhs):
    """Checks whether all Comparators are equal to rhs.

    Args:
      # rhs: can be anything

    Returns:
      bool
    """

    for comparator in self._comparators:
      if not comparator.equals(rhs):
        return False

    return True

  def __repr__(self):
    return '<AND %s>' % str(self._comparators)


class Or(Comparator):
  """Evaluates one or more Comparators on RHS and returns an OR of the results.
  """

  def __init__(self, *args):
    """Initialize.

    Args:
      *args: One or more Mox comparators
    """

    self._comparators = args

  def equals(self, rhs):
    """Checks whether any Comparator is equal to rhs.

    Args:
      # rhs: can be anything

    Returns:
      bool
    """

    for comparator in self._comparators:
      if comparator.equals(rhs):
        return True

    return False

  def __repr__(self):
    return '<OR %s>' % str(self._comparators)


class Func(Comparator):
  """Call a function that should verify the parameter passed in is correct.

  You may need the ability to perform more advanced operations on the parameter
  in order to validate it.  You can use this to have a callable validate any
  parameter. The callable should return either True or False.


  Example:

  def myParamValidator(param):
    # Advanced logic here
    return True

  mock_dao.DoSomething(Func(myParamValidator), true)
  """

  def __init__(self, func):
    """Initialize.

    Args:
      func: callable that takes one parameter and returns a bool
    """

    self._func = func

  def equals(self, rhs):
    """Test whether rhs passes the function test.

    rhs is passed into func.

    Args:
      rhs: any python object

    Returns:
      the result of func(rhs)
    """

    return self._func(rhs)

  def __repr__(self):
    return str(self._func)


class IgnoreArg(Comparator):
  """Ignore an argument.

  This can be used when we don't care about an argument of a method call.

  Example:
  # Check if CastMagic is called with 3 as first arg and 'disappear' as third.
  mymock.CastMagic(3, IgnoreArg(), 'disappear')
  """

  def equals(self, unused_rhs):
    """Ignores arguments and returns True.

    Args:
      unused_rhs: any python object

    Returns:
      always returns True
    """

    return True

  def __repr__(self):
    return '<IgnoreArg>'


class MethodGroup(object):
  """Base class containing common behaviour for MethodGroups."""

  def __init__(self, group_name):
    self._group_name = group_name

  def group_name(self):
    return self._group_name

  def __str__(self):
    return '<%s "%s">' % (self.__class__.__name__, self._group_name)

  def AddMethod(self, mock_method):
    raise NotImplementedError

  def MethodCalled(self, mock_method):
    raise NotImplementedError

  def IsSatisfied(self):
    raise NotImplementedError

class UnorderedGroup(MethodGroup):
  """UnorderedGroup holds a set of method calls that may occur in any order.

  This construct is helpful for non-deterministic events, such as iterating
  over the keys of a dict.
  """

  def __init__(self, group_name):
    super(UnorderedGroup, self).__init__(group_name)
    self._methods = []

  def AddMethod(self, mock_method):
    """Add a method to this group.

    Args:
      mock_method: A mock method to be added to this group.
    """

    self._methods.append(mock_method)

  def MethodCalled(self, mock_method):
    """Remove a method call from the group.

    If the method is not in the set, an UnexpectedMethodCallError will be
    raised.

    Args:
      mock_method: a mock method that should be equal to a method in the group.

    Returns:
      The mock method from the group

    Raises:
      UnexpectedMethodCallError if the mock_method was not in the group.
    """

    # Check to see if this method exists, and if so, remove it from the set
    # and return it.
    for method in self._methods:
      if method == mock_method:
        # Remove the called mock_method instead of the method in the group.
        # The called method will match any comparators when equality is checked
        # during removal.  The method in the group could pass a comparator to
        # another comparator during the equality check.
        self._methods.remove(mock_method)

        # If this group is not empty, put it back at the head of the queue.
        if not self.IsSatisfied():
          mock_method._call_queue.appendleft(self)

        return self, method

    raise UnexpectedMethodCallError(mock_method, self)

  def IsSatisfied(self):
    """Return True if there are not any methods in this group."""

    return len(self._methods) == 0


class MultipleTimesGroup(MethodGroup):
  """MultipleTimesGroup holds methods that may be called any number of times.

  Note: Each method must be called at least once.

  This is helpful, if you don't know or care how many times a method is called.
  """

  def __init__(self, group_name):
    super(MultipleTimesGroup, self).__init__(group_name)
    self._methods = set()
    self._methods_left = set()

  def AddMethod(self, mock_method):
    """Add a method to this group.

    Args:
      mock_method: A mock method to be added to this group.
    """

    self._methods.add(mock_method)
    self._methods_left.add(mock_method)

  def MethodCalled(self, mock_method):
    """Remove a method call from the group.

    If the method is not in the set, an UnexpectedMethodCallError will be
    raised.

    Args:
      mock_method: a mock method that should be equal to a method in the group.

    Returns:
      The mock method from the group

    Raises:
      UnexpectedMethodCallError if the mock_method was not in the group.
    """

    # Check to see if this method exists, and if so add it to the set of
    # called methods.
    for method in self._methods:
      if method == mock_method:
        self._methods_left.discard(method)
        # Always put this group back on top of the queue, because we don't know
        # when we are done.
        mock_method._call_queue.appendleft(self)
        return self, method

    if self.IsSatisfied():
      next_method = mock_method._PopNextMethod();
      return next_method, None
    else:
      raise UnexpectedMethodCallError(mock_method, self)

  def IsSatisfied(self):
    """Return True if all methods in this group are called at least once."""
    return len(self._methods_left) == 0


class MoxMetaTestBase(type):
  """Metaclass to add mox cleanup and verification to every test.

  As the mox unit testing class is being constructed (MoxTestBase or a
  subclass), this metaclass will modify all test functions to call the
  CleanUpMox method of the test class after they finish. This means that
  unstubbing and verifying will happen for every test with no additional code,
  and any failures will result in test failures as opposed to errors.
  """

  def __init__(cls, name, bases, d):
    type.__init__(cls, name, bases, d)

    # also get all the attributes from the base classes to account
    # for a case when test class is not the immediate child of MoxTestBase
    for base in bases:
      for attr_name in dir(base):
        if attr_name not in d:
          d[attr_name] = getattr(base, attr_name)

    for func_name, func in d.items():
      if func_name.startswith('test') and callable(func):
        setattr(cls, func_name, MoxMetaTestBase.CleanUpTest(cls, func))

  @staticmethod
  def CleanUpTest(cls, func):
    """Adds Mox cleanup code to any MoxTestBase method.

    Always unsets stubs after a test. Will verify all mocks for tests that
    otherwise pass.

    Args:
      cls: MoxTestBase or subclass; the class whose test method we are altering.
      func: method; the method of the MoxTestBase test class we wish to alter.

    Returns:
      The modified method.
    """
    def new_method(self, *args, **kwargs):
      mox_obj = getattr(self, 'mox', None)
      stubout_obj = getattr(self, 'stubs', None)
      cleanup_mox = False
      cleanup_stubout = False
      if mox_obj and isinstance(mox_obj, Mox):
        cleanup_mox = True
      if stubout_obj and isinstance(stubout_obj, stubout.StubOutForTesting):
        cleanup_stubout = True
      try:
        func(self, *args, **kwargs)
      finally:
        if cleanup_mox:
          mox_obj.UnsetStubs()
        if cleanup_stubout:
          stubout_obj.UnsetAll()
          stubout_obj.SmartUnsetAll()
      if cleanup_mox:
        mox_obj.VerifyAll()
    new_method.__name__ = func.__name__
    new_method.__doc__ = func.__doc__
    new_method.__module__ = func.__module__
    return new_method


class MoxTestBase(unittest.TestCase):
  """Convenience test class to make stubbing easier.

  Sets up a "mox" attribute which is an instance of Mox (any mox tests will
  want this), and a "stubs" attribute that is an instance of StubOutForTesting
  (needed at times). Also automatically unsets any stubs and verifies that all
  mock methods have been called at the end of each test, eliminating boilerplate
  code.
  """

  __metaclass__ = MoxMetaTestBase

  def setUp(self):
    super(MoxTestBase, self).setUp()
    self.mox = Mox()
    self.stubs = stubout.StubOutForTesting()
