import markovify
from nltk import pos_tag
import re
import logging 
logging.basicConfig(level=logging.INFO)


logging.info("Setting up models...")
one_word_pattern = re.compile(r'(.*\s|\A)(\w*)\.*$')
two_word_pattern = re.compile(r'(.*\s|\A)(\w*)\s(\w*)\.*$')


# class POSifiedText(markovify.Text):
    # def word_split(self, sentence):
        # words = re.split(self.word_split_pattern, sentence)
        # words = [ "::".join(tag) for tag in pos_tag(words) ]
        # return words

    # def word_join(self, words):
        # sentence = " ".join(word.split("::")[0] for word in words)
        # return sentence

# text =  open('speech sample.txt', 'r', encoding="utf8")
# two_word_model = POSifiedText(text, state_size = 2)
# text =  open('speech sample.txt', 'r', encoding="utf8")
# one_word_model = POSifiedText(text, state_size = 1)
text =  open('speech sample 5.txt', 'r', encoding="utf8")
two_word_model = markovify.Text(text, state_size = 2)
text =  open('speech sample 5.txt', 'r', encoding="utf8")
one_word_model = markovify.Text(text, state_size = 1)

logging.info("Setup complete!")


def get_last_words(sentence):
	try:
		words = re.findall(two_word_pattern, sentence)[0][-2:]
		return words
	except:
		logging.info("Could not return two words, will use only the last word")
	
	try:
		word = re.findall(one_word_pattern, sentence)[0][-1]
		return word
	except:
		logging.info("Could not return one word")
	
	return None
		
def test_get_words():
	print(get_last_words('and so the wheel turns...'))
	print(get_last_words('Boy...'))
	print(get_last_words('“But it is,” returned she; “for Mrs. Long has just been here, and \n'\
	'she told me all about it.”\n Mr. Bennet made no answer.\n“Do you not want to know who has taken it?”'\
	'cried his wife impatiently....'))
	
#formats the completion the way we want it
def remove_fist_words(word, ammount):
	return '...' + ' '.join(word.split(' ')[ammount:])
	
#This return a completion if the model can handle the sentence and None if not
def complete_sentence(sentence):
	print("-----------------------------------------------------------------")
	print(sentence)
	ending = get_last_words(sentence)
	
	completion = None
	if type(ending) is tuple: #if we have a two word list
		try:#if it crashes abort this
			while completion == None:#if the sentence isn't coherent it will generate none
				completion = two_word_model.make_sentence(init_state = ending)
				return remove_fist_words(completion, 2)
		except:
			pass
		# except:
			# logging.info("Could not find the word %s followed by the word %s"%(ending[0],ending[1]))
			# try:
				# completion = one_word_model.make_sentence_with_start(ending[1])
				# return remove_fist_words(completion, 1)
			# except:
				# logging.info("Could not complete this ending: %s, %s"%(ending[0], ending[1]))
	# elif type(ending) is str:
		# try:
			# while completion == None:
				# completion = one_word_model.make_sentence_with_start(ending)
				# return remove_fist_words(completion, 1)
		# except:
			# logging.info("Word not in text:%s"%ending)
	return completion
			

def test_model(tries = 5):
	for i in range(tries):
		print(complete_sentence ('gone well...'))
	for i in range(tries):
		print(complete_sentence('gone...'))

print(complete_sentence("Not sure what it's from, though..."))

