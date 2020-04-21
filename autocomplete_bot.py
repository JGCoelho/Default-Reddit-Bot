import praw, datetime, time
import reddit_config as config
import sqlite3 as sql
import reddit_config as config
import logging 
from markov import *

# logging.basicConfig(filename="log.log", level=logging.INFO,
					# filemode="w")


SUB_NAME = "books"
NUM_OF_POSTS = 20

					
#the database has the following parameters:
#"CREATE TABLE comments (id INTEGER PRIMARY KEY, comment_id TEXT, user TEXT, body TEXT, completion TEXT, date INTEGER)"
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
		print(row[0])
		print(row[1])
	
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
	r = login()


	comment_count = 0
	comments_found = []

	connection, cursor = open_database()

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
				logging.info('\"'+comment.body+'\"')
				
				completion = complete_sentence(comment.body)
				logging.info('Completion: %s'%completion)
				if completion != None:
					add_to_database(comment, completion, connection, cursor)
			

	logging.info("We found the following comments:")
	for comment in comments_found:
		logging.info("----------------------------------------------------------------------------\n"\
					"%s\n%s"%(comment[0], comment[1]))
	
	
	show_database_completions(cursor)
				
				
run()

				

				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				