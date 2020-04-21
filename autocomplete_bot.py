import markovify
from nltk import pos_tag
import re
one_word_pattern = re.compile(r'(.*\s|\A)(\w*)\.*$')
two_word_pattern = re.compile(r'(.*\s|\A)(\w*)\s(\w*)\.*$')
import sqlite3 as sql
import reddit_config as config
import praw, datetime, time
import logging 
logging.basicConfig(level=logging.INFO)



SUB_NAME = "freefolk"
NUM_OF_POSTS = 30



		
#the database has the following parameters:
#"CREATE TABLE comments (id INTEGER PRIMARY KEY, comment_id TEXT, user TEXT, body TEXT, completion TEXT, date INTEGER)"
class Database():
	def __init__(self,name = config.database):
		def self.
def open_database():
	logging.info("Opening database...")
	connection = sql.connect(config.database)
	cursor = connection.cursor()
	logging.info("Database Open")
	return connection, cursor
	
def show_database_content(cursor):
	print("This is the content of the database:")
	matches = cursor.execute("SELECT * FROM comments").fetchall()
	for row in matches:
		print(row)
		
def show_database_completions(cursor):
	print("\n-------------------------------------------------------\n"
		"Those are the completions in the database:")
	matches = cursor.execute("SELECT body, completion FROM comments").fetchall()
	for row in matches:
		print("-------------------------------------------------------")
		if len(row[0]) > 50:
			print("[...]" + row[0][-30:])
		else:
			print(row[0])
		print(row[1])
		
def delete_entire_database(connection,cursor):
	print("Are you sure? (y/n)")
	confirmation = input()
	if confirmation =="y":
		cur.execute("DELETE FROM comments")
		con.commit()
	
def check_if_replied_to_comment(comment, cursor):
	matches = cursor.execute("SELECT COUNT(*) FROM comments "
				"WHERE comment_id = '%s' LIMIT 1"%comment.fullname).fetchall()[0][0]
	if matches > 0:
		return True
	return False
	
def adapt_datetime(ts):
    return int(time.mktime(ts.timetuple()))
	
def add_to_database(comment, completion, connection, cursor):
	logging.info("Adding comment to database...")
	cursor.execute("INSERT INTO comments (comment_id, user, body, completion, date) "\
		"VALUES (?, ?, ?, ?, ?)", (comment.fullname, comment.author.name, comment.body,
		completion, adapt_datetime(datetime.date.today())))
	connection.commit()
	logging.info("Comment added!")

#########################################################################################
connection, cursor = open_database()
#########################################################################################

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
	#print("-----------------------------------------------------------------")
	#print(sentence)
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



				
	
def login():
	logging.info("Logging in...")
	r = praw.Reddit(username = config.user, 
				password = config.password,
				client_id = config.client_id,
				client_secret = config.client_secret,
				user_agent = "Priced In Bot")
	logging.info("Logged!")
	return r
	
def run():
	logging.info("Setting up models...")


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
	
	r = login()


	comment_count = 0
	comments_found = []

	logging.info("Opening sub...")
	sub = r.subreddit(SUB_NAME)
	logging.info("Sub opened!")
	logging.info("Getting posts...")
	hot_submissions = sub.hot(limit = NUM_OF_POSTS)

	for post in hot_submissions:
		logging.info("-------------------------------------------------------"\
			"\nPost: www.reddit.com/r/%s/comments/%s/"%(SUB_NAME, post.id))
		if post.archived:#if the post was archived then ignore
				logging.info("Post was archived")
				continue
		
		#without this the code breaks when reading a 'more comments'
		post.comments.replace_more(limit=0)
		all_comments = post.comments.list()
		# logging.info("This is the ammount of comments: %s"%(len(all_comments)))
		for comment in all_comments:
			if comment.body[len(comment.body) - 3:] == "...":
				if check_if_replied_to_comment(comment, cursor):
					logging.info("Already replied to comment")
					continue #skips this if it has already replied to comment
				logging.info("Found matching comment!!!")
				logging.info(comment.body[-50:])
				
				completion = complete_sentence(comment.body)
				logging.info('Completion: %s'%completion)
				if completion != None:
					add_to_database(comment, completion, connection, cursor)
			

	logging.info("We found the following comments:")
	for comment in comments_found:
		logging.info("----------------------------------------------------------------------------\n"\
					"%s\n%s"%(comment[0], comment[1]))
	
	
	show_database_completions(cursor)
				
				
#run()

				

				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				