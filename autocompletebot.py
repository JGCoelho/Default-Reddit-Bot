import markovify
import re
import sqlite3 as sql
import reddit_config as config
import praw, datetime, time
import logging 
logging.basicConfig(level=logging.INFO)







	
#####################################################################################################################
#####################################################################################################################
logging.info("Loading natural language library...")

#the first one matches only phrases with only one word.
#the second one matches the last two words in a phrase with two words
one_word_pattern = re.compile(r'^(\w*)\.*$')
two_word_pattern = re.compile(r'(.*\s|\A)(\S*\s\w*)\.*$')

# import nltk

# class POSifiedText(markovify.Text):
    # def word_split(self, sentence):
        # words = re.split(self.word_split_pattern, sentence)
        # words = [ "::".join(tag) for tag in nltk.pos_tag(words) ]
        # return words

    # def word_join(self, words):
        # sentence = " ".join(word.split("::")[0] for word in words)
        # return sentence

# logging.info("Setting up one two model...")		
# with open("samples\\" + config.SAMPLE_FILE, 'r', encoding="utf8") as text:
	# two_word_model = POSifiedText(text, state_size = 2)
	# two_word_model = two_word_model.compile(inplace = True)
	
	
# with open("samples\\" + config.SAMPLE_FILE, 'r', encoding="utf8") as text:
	# one_word_model = POSifiedText(text, state_size = 1)
	# one_word_model = two_word_model.compile(inplace = True)
	

	
with open("samples\\" + config.SAMPLE_FILE, 'r', encoding="utf8") as text:
	two_word_model = markovify.Text(text, state_size = 2)
	two_word_model = two_word_model.compile()
	
with open("samples\\" + config.SAMPLE_FILE, 'r', encoding="utf8") as text:
	one_word_model = markovify.Text(text, state_size = 1)
	one_word_model = one_word_model.compile()
	
logging.info("Setup complete.")

#####################################################################################################################


######################################################################################################################		
#the database of comments that have been completed
#"CREATE TABLE comments (id INTEGER PRIMARY KEY, comment_id TEXT, user TEXT, body TEXT, completion TEXT, date INTEGER)"
#database of user
#"CREATE TABLE banned (id INTEGER PRIMARY KEY, user TEXT)"
#table of comments the bot couldn't complete (for debbuging)
#"CREATE TABLE failures (id INTEGER PRIMARY KEY, body TEXT)"
#database of all comments replied
######################################################################################################################
class Database:
	def __init__(self, database = config.database):
		self.database = database
		self.connection = sql.connect(database)
		self.cursor = self.connection.cursor()
		
	def open_database(self, database = config.database):
		self.connection = sql.connect(database)
		self.cursor = self.connection.cursor()
		return self.connection, self.cursor
	
	def show_content(self):
		print("This is the content of the database:")
		matches = self.cursor.execute("SELECT * FROM comments ORDER BY id").fetchall()
		for row in matches:
			print(row)
	
	def show_completions(self):
		print("\n-------------------------------------------------------\n"
			"Those are the completions in the database:")
		matches = self.cursor.execute("SELECT body, completion FROM comments ORDER BY id").fetchall()
		for row in matches:
			print("-------------------------------------------------------")
			if len(row[0]) > 50:
				print("[...]" + row[0][-30:])
			else:
				print(row[0])
			print(row[1])
			
	def get_size(self):
		size = self.cursor.execute("SELECT COUNT(*) FROM comments").fetchall()[0][0]
		return size
			
	def delete_entire_database(self):
		print("Are you sure? (y/n)")
		confirmation = input()
		if confirmation =="y":
			self.cursor.execute("DELETE FROM comments")
			self.connection.commit()
	
	def check_replied(self, comment):
		matches = self.cursor.execute("SELECT COUNT(*) FROM comments "
					"WHERE comment_id = '%s' LIMIT 1"%comment.fullname).fetchall()[0][0]
		if matches > 0:
			return True
		return False
	
	def adapt_datetime(self,ts):
		return int(time.mktime(ts.timetuple()))
	
	def add_to(self, comment, completion):
		logging.info("Adding comment to database...")
		self.cursor.execute("INSERT INTO comments (comment_id, user, body, completion, date) "\
			"VALUES (?, ?, ?, ?, ?)", (comment.fullname, comment.author.name, comment.body,
			completion, self.adapt_datetime(datetime.date.today())))
		self.connection.commit()
		logging.info("Comment added!!!!!!!!")
		
	def ban_author(self, author):
		logging.info("Banned %s"%(author.name))
		self.cursor.execute("INSERT INTO banned (user) VALUES (?)", (author.name,))
		self.connection.commit()
		
	def show_banned(self):
		matches = self.cursor.execute("SELECT * FROM banned ORDER BY id").fetchall()
		for row in matches:
			print(row)
	
	def check_banned(self, author):
		matches = self.cursor.execute("SELECT COUNT(*) FROM banned "
					"WHERE user = ? LIMIT 1",(author.name,)).fetchall()[0][0]
		if matches > 0:
			return True
		return False
		
	def close_database(self):
		self.connection.commit()
		self.connection.close()
		
	def add_failure(self, comment):
		logging.info("Adding comment to failures...")
		self.cursor.execute("INSERT INTO failures (body) "\
			"VALUES (?)", (comment.body,))
		self.connection.commit()
		logging.info("Comment added to failures.")
		
	def show_failures(self):
		print("\n-------------------------------------------------------\n"
			"Those are the failures in the database:")
		matches = self.cursor.execute("SELECT * FROM failures ORDER BY id").fetchall()
		for row in matches:
			print("-------------------------------------------------------")
			if len(row[1]) > 30:
				print("[...]" + row[1][-30:])
			else:
				print(row[1])
			
	def delete_failures(self):
		print("Are you sure? (y/n)")
		confirmation = input()
		if confirmation =="y":
			self.cursor.execute("DELETE FROM failures")
			self.connection.commit()
	
		
	


#########################################################################################
#########################################################################################
#########################################################################################

def get_last_words(sentence):
	try:
		words = re.findall(two_word_pattern, sentence)[0][1]
		return words
	except:
		logging.info("Could not return two words")
	return None
	
def get_last_word(sentence):
	try:
		words = re.findall(one_word_pattern, sentence)[0]
		return words
	except:
		logging.info("Could not return any word")
	return None
		
#formats the completion the way we want it
def remove_fist_words(word, amount):
	return '...' + ' '.join(word.split(' ')[amount:])
	
#This return a completion if the model can handle the sentence and None if not
def complete_sentence(sentence):
	ending = get_last_words(sentence)
	
	completion = None
	if ending != None:
		try:
			while completion == None:
				#print("We have this value for the ending: %s"%ending)
				completion = two_word_model.make_sentence_with_start(ending)
				if len(completion) < config.IDEAL_LEN:
					completion += " "+two_word_model.make_sentence()
				#print("We obtained the completion %s"%completion)
				return remove_fist_words(completion, 2)
		except:
			pass
	else:
		ending = get_last_word(sentence)
		if ending != None:
			try:
				while completion == None:
					#("We have this value for the ending: %s"%ending)
					completion = one_word_model.make_sentence(initial_state = ending)
					if len(completion) < config.IDEAL_LEN:
						completion += " "+two_word_model.make_sentence()
					
					#print("We obtained the completion %s"%completion)
					return remove_fist_words(completion, 1)
			except:
				pass
	return completion
			


#########################################################################################
#########################################################################################
#########################################################################################
				
	
def login():
	logging.info("Logging in...")
	r = praw.Reddit(username = config.user, 
				password = config.password,
				client_id = config.client_id,
				client_secret = config.client_secret,
				user_agent = "sandocomplete")
	logging.info("Logged!")
	return r
	
def check_inbox(reddit, database):
	for reply in reddit.inbox.comment_replies():
		if config.SAFE_WORD in reply.body and not database.check_banned(reply.author):
			logging.info(reply.author)
			reply.reply("*The bot commits sepuku.*")
			database.ban_author(reply.author)
			#logging.info("%s is banned!"%reply.author.name)
			
def reply_completion(comment, completion):
	message = " {}\n\n {}\n\n {} {}".format(completion,
		"-------------------------------------------------------",
		"^^I ^^am ^^a ^^bot, ^^this ^^reply ^^was ^^perfomed ^^automatically.",
		"^^Reply ^^!NOMORE ^^if ^^you ^^would ^^like ^^me ^^to ^^stop ^^replying ^^to ^^your ^^comments.")
	comment.reply(message)
	
def delete_bad_comments(reddit):
	user_comments = reddit.user.me().comments.new(limit=10)
	for comment in user_comments:
		if comment.score < 1:
			logging.info("Deleted a comment.")
			comment.delete()

			
	
def run():
	replied_comments = []
	database = Database()
	reddit = login()
	
	logging.info("Checking inbox.")
	check_inbox(reddit,database)
	
	logging.info("Deleting bad replies.")
	delete_bad_comments(reddit)
	
	logging.info("Opening sub...")
	sub = reddit.subreddit(config.SUB_NAME)
	logging.info("Sub opened!")
	logging.info("Getting posts...")
	hot_submissions = sub.hot(limit = config.NUM_OF_POSTS)
	
	
	for post in hot_submissions:
		logging.info("-------------------------------------------------------\n"+
					post.url)
		if post.archived:
				logging.info("Post was archived")
				continue
		
		#without this the code breaks when reading a 'more comments'
		post.comments.replace_more(limit=0)
		all_comments = post.comments.list()
		
		for comment in all_comments:
			if not comment.author:
				logging.info("Comment deleted")
				continue
			if database.check_banned(comment.author):
				logging.info("Author is banned")
				continue
			if comment.body[len(comment.body) - 3:] == "...":
				if database.check_replied(comment):
					logging.info("Already replied to comment")
					continue #skips this if it has already replied to comment
				logging.info("Found matching comment!")
				logging.info(comment.body[-50:])
				
				completion = complete_sentence(comment.body)
				logging.info('Completion: %s'%completion)
				if completion != None and "::" not in completion:
					#reply_completion(comment, completion)
					#database.add_to(comment, completion)
					replied_comments.append([post.url,comment.body[-50:],completion])
				else:
					#database.add_failure(comment)
					pass
	#database.show_completions()
	#database.show_failures()
	logging.info("-------------------------------------------------------\nThe replies in this run:")
	for comment in replied_comments:
		logging.info("-------------------------------------------------------\n{}"\
			"\n{}\n{}".format(comment[0], comment[1], comment[2]))
			
	logging.info("-------------------------------------------------------\n" +
		"In this run we added %s comments to the database.\n"%total_of_comments +
		"The database has a total of %s comments."%database.get_size())
		
	database.connection.close()

				

				

				
endings = ["What is...", "to focus..."]
for sentence in endings:
	ending = get_last_words(sentence)
	print("-----------------------------------------------------------")
	for i in range (5):
		try:
			print(complete_sentence(ending))
		except Exception as e:
			logging.critical(e, exc_info=True)
				

				
				
				
				
				
				
				
				
				
				
				
				