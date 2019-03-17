from google.appengine.ext import db

from model import Person
from server_tests_base import ServerTestsBase
import utils


class InputEscapingTests(ServerTestsBase):

    SCRIPT_CONTENT = '<script type="text/javascript">alert("hello")</script>'

    def test_record_content_escaped(self):
        self.go('/haiti/create')
        create_form = self.s.doc.cssselect_one('form')
        # Stuff that's expected to be regular text (i.e., not links or something
        # like that) is escaped automatically by Django, so we don't need to
        # test the complete list of fields. We'll test a few of them just to
        # make sure Django autoescaping doesn't accidentally get disabled.
        self.s.submit(create_form,
                      own_info='no',
                      given_name=InputEscapingTests.SCRIPT_CONTENT,
                      family_name=InputEscapingTests.SCRIPT_CONTENT,
                      author_name=InputEscapingTests.SCRIPT_CONTENT,
                      description=InputEscapingTests.SCRIPT_CONTENT)
        # Check that the record creation went through and we're on the view page.
        assert 'hello' in self.s.doc.content
        # Check that the <script> tag is not included.
        assert '<script>' not in self.s.doc.content
        # Check that the content was included, but escaped.
        assert '&lt;' in self.s.doc.content

    def test_note_content_escaped(self):
        db.put(Person(
            key_name='haiti:test.google.com/person.123',
            repo='haiti',
            author_name='_test1_author_name',
            entry_date=ServerTestsBase.TEST_DATETIME,
            full_name='_test1_full_name',
            sex='male',
            date_of_birth='1970-01-01',
            age='50-60',
            latest_status='believed_missing'
        ))
        self.go('/haiti/view?id=test.google.com/person.123&lang=en')
        self.s.submit(self.s.doc.cssselect_one('input.add-note'))
        note_form = self.s.doc.cssselect_one('form')
        params = {'own_info': 'no',
                  'given_name': InputEscapingTests.SCRIPT_CONTENT,
                  'family_name': InputEscapingTests.SCRIPT_CONTENT,
                  'author_name': InputEscapingTests.SCRIPT_CONTENT,
                  'text': InputEscapingTests.SCRIPT_CONTENT}
        details_page = self.s.submit(note_form, **params)
