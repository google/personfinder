import random


NUM_NAMES_PER_LANG = 1000000
ENGLISH_NAME_MIN_LEN = 3
ENGLISH_NAME_MAX_LEN = 10
LATIN_ALPHABETS = 'abcdefghijklmnopqrstuvwxyz'


def generate_english_name_component():
	name_len = random.randint(ENGLISH_NAME_MIN_LEN, ENGLISH_NAME_MAX_LEN)
	return ''.join(random.choice(LATIN_ALPHABETS) for _ in xrange(name_len))


if __name__ == '__main__':
	random.seed(0)
	
	with open('app/japanese_name_location_dict.txt') as f:
		ja_words = [line.rstrip('\n').split('\t')[0] for line in f]
	ja_output_names = set()
	while len(ja_output_names) < NUM_NAMES_PER_LANG:
		ja_output_names.add('%s %s' % (random.choice(ja_words), random.choice(ja_words)))

	en_output_names = set()
	while len(en_output_names) < NUM_NAMES_PER_LANG:
		en_output_names.add('%s %s' % (
			generate_english_name_component(), generate_english_name_component()))

	output_names = ja_output_names | en_output_names
	for name in random.sample(output_names, len(output_names)):
		print name
