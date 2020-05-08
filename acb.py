import markovify
import re
import json
import praw
import datetime
import time
import sqlite3
import random
import config as config
import logging
import spacy
# import nltk.data

logging.basicConfig(filename="log.log", level=logging.INFO,
                    filemode="w")
# logging.basicConfig(level=logging.INFO)

nlp = spacy.load('en')
# tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

flawed_utf_patt = re.compile(r'\\x\.*')
quote_patt = re.compile("\"")
space_patt = re.compile(r'\s+')
nt_patt = re.compile(r'\s+n\'t')
s_patt = re.compile(r'\s+\'s')
d_patt = re.compile(r'\s+\'d')
ve_patt = re.compile(r'\s+\'ve')
ll_patt = re.compile(r'\s+\'ll')
newline_patt = re.compile(r'\s\\n\s+')

##################################################################
##################################################################
##################################################################
# methods to create, save and load models
##################################################################


class MarkovPT(markovify.Text):
    def word_split(self, sentence):
        return ["::".join((word.orth_, word.pos_)) for word in nlp(sentence)]

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence

    # here we need to get the two last words but forget
    # the ellipsis "..."
    def get_last_words(self, sentence):
        split_sentence = self.word_split(sentence)
        last_two = split_sentence[-3:-1]
        last_two = self.word_join(last_two)
        return last_two

    def format_msg(self, msg):
        # capitalize each phrase
        for ponct in [". ", "! ", "? "]:
            sentences = msg.split(ponct)
            for index in range(1, len(sentences)):
                sentences[index] = (sentences[index][0].upper()
                                    + sentences[index][1:])
            msg = ponct.join(sentences)

        # now we remove the first two words
        split_sentence = self.word_split(msg)
        if "::PUNCT" not in split_sentence[2]:
            msg = self.word_join(split_sentence[2:])
        else:
            msg = self.word_join(split_sentence[3:])

        # then we format the text
        msg = re.sub(space_patt, " ", msg)
        msg = re.sub(flawed_utf_patt, "", msg)
        msg = re.sub(quote_patt, "", msg)
        msg = re.sub(nt_patt, "n't", msg)
        msg = re.sub(s_patt, "'s", msg)
        msg = re.sub(d_patt, "'d", msg)
        msg = re.sub(ve_patt, "'ve", msg)
        msg = re.sub(ll_patt, "'ll", msg)
        msg = re.sub(newline_patt, " ", msg)
        msg = re.sub(u'\\s([?\\.\'!,;"](?:\\s|$))', r'\1', msg)
        msg = "..." + msg
        return msg

    def make_msg(self, model):
        logging.info("Generating sentence")
        min_size = 200
        max_size = 240
        entire_sentence = ""
        while len(entire_sentence) < min_size:
            if len(entire_sentence) != 0:
                entire_sentence += " "
            sentence = None
            while sentence is None:
                sentence = \
                    model.make_short_sentence(max_size - len(entire_sentence))

            if sentence[-1] == ",":
                sentence = sentence[:-1] + "."
            elif sentence[-1] not in ["?", "!", ".", "\""]:
                sentence = sentence + "."
            entire_sentence += sentence
        # the machado model has some accented
        # characters that for some reason don't
        # get formated nicely. In this step
        # we remove them and do some more formatting
        entire_sentence = self.format_msg(entire_sentence)
        return entire_sentence

    def complete_sentence(self, sentence, max_tries=5):
        last_words = self.get_last_words(sentence)
        tries = 0
        completion = None
        while completion is None and tries < max_tries:
            try:
                completion = self.make_sentence_with_start(
                    last_words
                )
                completion = self.format_msg(completion)
            except Exception as e:
                tries += 1
                logging.info(e)
        return completion

    @classmethod
    def get_crypto(cls):
        return load_model_from_json("Crypto")

    @classmethod
    def get_sando(cls):
        return load_model_from_json("Sando")

    @classmethod
    def get_asoiaf(cls):
        return load_model_from_json("asoiaf")


def save_model_as_json(text_model, file_name):
    model_json = text_model.to_json()
    with open('models\\' + file_name + '.json', 'w') as outfile:
        json.dump(model_json, outfile)


def load_model_from_json(file_name):
    logging.info("Opening model: {}".format(file_name))
    with open('models\\' + file_name + '.json') as json_file:
        return MarkovPT.from_json(json.load(json_file))


def model_and_save(file_name, state_size=2):
    # also returns the model
    with open('samples\\' + file_name + '.txt', encoding="utf-8") as file:
        model = MarkovPT(file.read(), state_size=state_size)
    save_model_as_json(model, file_name)
    return model

##################################################################
##################################################################
##################################################################
# the database of comments that have been completed
# "CREATE TABLE comments (id INTEGER PRIMARY KEY, comment_id TEXT,
#  user TEXT, body TEXT, completion TEXT, date INTEGER)"
# database of user
# "CREATE TABLE banned (id INTEGER PRIMARY KEY, user TEXT)"
# table of comments the bot couldn't complete (for debbuging)
# "CREATE TABLE failures (id INTEGER PRIMARY KEY, body TEXT, comment_id TEXT)"
# database of all comments replied
##################################################################


class Database:
    def __init__(self, database=config.database):
        self.database = database
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    def open_database(self, database=config.database):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()
        return self.connection, self.cursor

    def show_content(self):
        print("This is the content of the database:")
        matches = self.cursor.execute("SELECT * FROM comments"
                                      " ORDER BY id").fetchall()
        for row in matches:
            print(row)

    def show_completions(self):
        print("\n-------------------------------------------------------\n"
              "Those are the completions in the database:")
        matches = self.cursor.execute("SELECT body, completion "
                                      "FROM comments ORDER BY id").fetchall()
        for row in matches:
            print("-------------------------------------------------------")
            if len(row[0]) > 50:
                print("[...]" + row[0][-30:])
            else:
                print(row[0])
            print(row[1])

    def get_size(self):
        size = self.cursor.execute("SELECT COUNT(*) "
                                   "FROM comments").fetchall()[0][0]
        return size

    def delete_entire_database(self):
        print("Are you sure? (y/n)")
        confirmation = input()
        if confirmation == "y":
            self.cursor.execute("DELETE FROM comments")
            self.connection.commit()

    def check_replied(self, comment):
        matches = \
            self.cursor.execute("SELECT COUNT(*) FROM comments "
                                "WHERE comment_id = '%s' LIMIT 1"
                                % comment.fullname).fetchall()[0][0]
        if matches > 0:
            return True
        return False

    def adapt_datetime(self, ts):
        return int(time.mktime(ts.timetuple()))

    def add_to(self, comment, completion):
        logging.info("Adding comment to database...")
        self.cursor.execute("INSERT INTO comments (comment_id, user,"
                            " body, completion, date) VALUES (?, ?, ?, ?, ?)",
                            (comment.fullname, comment.author.name,
                             comment.body, completion,
                             self.adapt_datetime(datetime.date.today())))
        self.connection.commit()
        logging.info("Comment added!!!!!!!!")
        self.connection.commit()

    def ban_author(self, author):
        logging.info("Banned %s" % (author.name))
        self.cursor.execute("INSERT INTO banned (user) VALUES "
                            "(?)", (author.name,))
        self.connection.commit()

    def show_banned(self):
        matches = self.cursor.execute("SELECT * FROM "
                                      "banned ORDER BY id").fetchall()
        for row in matches:
            print(row)

    def check_banned(self, author):
        matches =\
            self.cursor.execute("SELECT COUNT(*) FROM banned "
                                "WHERE user = ? LIMIT 1",
                                (author.name,)).fetchall()[0][0]
        if matches > 0:
            return True
        return False

    def close_database(self):
        self.connection.close()

    def add_failure(self, comment):
        logging.info("Adding comment to failures...")
        self.cursor.execute("INSERT INTO failures (body, comment_id) "
                            "VALUES (?,?)", (comment.body, comment.id))
        self.connection.commit()
        logging.info("Comment added to failures.")

    def show_failures(self):
        print("\n-------------------------------------------------------\n"
              "Those are the failures in the database:")
        matches = self.cursor.execute("SELECT * FROM "
                                      "failures ORDER BY id").fetchall()
        for row in matches:
            print("-------------------------------------------------------")
            if len(row[1]) > 30:
                print("[...]" + row[1][-30:])
            else:
                print(row[1])

    def delete_failures(self):
        print("Are you sure? (y/n)")
        confirmation = input()
        if confirmation == "y":
            self.cursor.execute("DELETE FROM failures")
            self.connection.commit()

    def check_failure(self, comment):
        matches = self.cursor.execute("SELECT COUNT(*) FROM failures "
                                      "WHERE comment_id = ? LIMIT 1",
                                      (comment.id,)).fetchall()[0][0]
        if matches > 0:
            return True
        return False
##################################################################
##################################################################
##################################################################


def login():
    logging.info("Logging in...")
    r = praw.Reddit(username=config.user,
                    password=config.password,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    user_agent="sandocomplete")
    logging.info("Logged!")
    return r


def check_inbox(reddit, database):
    for reply in reddit.inbox.comment_replies():
        if config.SAFE_WORD in reply.body and\
          not database.check_banned(reply.author):
            logging.info(reply.author)
            ban_msg = random.choice(config.BAN_MSGS)
            reply.reply("*{}*".format(ban_msg))
            database.ban_author(reply.author)
            logging.info("%s is banned!" % reply.author.name)
            if reply.parent().author.name == config.user:
                reply.parent().delete()


def reply_completion(comment, completion):
    message = \
        " {}\n\n {}\n\n {} {}".format(
            completion,
            "-------------------------------------------------------",
            "^^I ^^am ^^a ^^bot, ^^this ^^reply ^^was ^^perfomed "
            "^^automatically.",
            "^^Reply ^^{} ^^to ^^stop ^^getting ^^replied ^^to.".format(
                config.SAFE_WORD))
    comment.reply(message)


def delete_bad_comments(reddit):
    user_comments = reddit.user.me().comments.new(limit=10)
    for comment in user_comments:
        if comment.score < 1:
            logging.info("Deleted a comment.")
            comment.delete()


def run(sub_name, model):
    logging.info(datetime.datetime.now())

    replied_comments = []
    database = Database()
    reddit = login()

    check_inbox(reddit, database)

    logging.info("Deleting bad replies.")
    delete_bad_comments(reddit)

    logging.info("Opening sub...")
    sub = reddit.subreddit(sub_name)
    logging.info("Sub opened!")
    logging.info("Getting posts...")
    hot_submissions = sub.hot(limit=config.NUM_OF_POSTS)

    for post in hot_submissions:
        logging.info("-----------------------------------"
                     "--------------------\n" + post.url)
        if post.archived or post.locked:
            logging.info("Post was archived or locked.")
            continue

        # without this the code breaks when reading a 'more comments'
        post.comments.replace_more(limit=0)
        all_comments = post.comments.list()

        for comment in all_comments:
            if not comment.author:
                logging.info("Couldn't find author.")
                continue
            if database.check_banned(comment.author):
                logging.info("Author is banned")
                continue
            if comment.body[len(comment.body) - 3:] == "...":
                if database.check_replied(comment):
                    logging.info("Already replied to comment")
                    continue  # skips this if it has already replied to comment
                logging.info("Found matching comment!")
                logging.info(comment.body[-50:])

                completion = model.complete_sentence(comment.body)
                logging.info('Completion: %s' % completion)
                if completion is not None and "::" not in completion:
                    reply_completion(comment, completion)
                    database.add_to(comment, completion)
                    replied_comments.append([post.url,
                                             comment.body[-50:], completion])
                else:
                    if not database.check_failure(comment):
                        database.add_failure(comment)
    # database.show_completions()
    # database.show_failures()
    logging.info("-------------------------------------------------------\n"
                 "The replies in this run:")
    for comment in replied_comments:
        logging.info("----------------------------------------------------"
                     "---\n{}\n{}\n{}".format(comment[0],
                                              comment[1], comment[2]))

    logging.info("-------------------------------------------------------\n" +
                 "In this run we added %s comments to the database.\n" %
                 len(replied_comments) +
                 "The database has a total of %s comments." %
                 database.get_size())

    database.cursor.execute("VACUUM;")
    database.connection.commit()
    database.connection.close()


def run_model(model, sub_name):
    try:
        logging.info("Running model on {}.".format(sub_name))
        run(sub_name, model)
    except Exception as e:
        logging.critical(e, exc_info=True)


if __name__ == "__main__":
    m = MarkovPT.get_sando()
    for i in range(10):
        print(m.complete_sentence("sure he was..."))
