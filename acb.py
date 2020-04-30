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
import nltk

logging.basicConfig(filename="log.log", level=logging.INFO,
                    filemode="w")
# logging.basicConfig(level=logging.INFO)

# the first one matches only phrases with only one word.
# the second one matches the last two words in a phrase with two words
ONE_WORD_PATTERN = re.compile(r'^(\w+)\.*$')
TWO_WORD_PATTERN = re.compile(r'(.*\s+|^)(\S+\s+\w+)\.*$')
THREE_WORD_PATTERN = re.compile(r'(.*\s+|^)(\S+\s+\S+\s+\w+)\.*$')
PUNC_FILTER = re.compile(r'([.!?]\s*)')
QUOTE_PATTERN = re.compile("\"")

##################################################################
##################################################################
##################################################################
# methods to create, save and load models
##################################################################


class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = ["::".join(tag) for tag in nltk.pos_tag(words)]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence


def save_model_as_json(text_model, file_name):
    model_json = text_model.to_json()
    with open('models\\' + file_name + '.json', 'w') as outfile:
        json.dump(model_json, outfile)


def load_model_from_json(file_name, pos=True):
    logging.info("Lendo modelo {}".format(file_name))
    with open(config.MODELS_FOLDER + file_name) as json_file:
        if pos:
            return POSifiedText.from_json(json.load(json_file))
        return markovify.Text.from_json(json.load(json_file))


def create_models_and_save(sample_file, output_name, pos=True):
    def create_model_and_save(state_size):
        with open(sample_file, 'r', encoding="utf-8") as file:
            if pos:
                model = POSifiedText(file, state_size)
                model_type = "pos"
            else:
                model = markovify.Text(file, state_size)
                model_type = "mark"
            save_model_as_json(model, output_name + " "
                               + str(state_size) + " " + model_type)
    for i in range(1, 4):  # 1, 2, 3
        create_model_and_save(i)

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


class Handler:
    # return the last words and the ammount of words it could extract.
    # tries to extract the most amount of words at the end.
    def __init__(self, model_dict, pos=True):
        self.models = \
            {'model1': load_model_from_json(model_dict['model1'], pos),
             'model2': load_model_from_json(model_dict['model2'], pos),
             'model3': load_model_from_json(model_dict['model3'], pos)}

    def get_last_words(self, sentence):
        # logging.info("Extracting ending of sentence \"{}\"".format(sentence))
        try:
            words = re.findall(THREE_WORD_PATTERN, sentence)[0][1]
            return words, 3
        except IndexError:
            logging.info("Could not return three words")
            try:
                words = re.findall(TWO_WORD_PATTERN, sentence)[0][1]
                return words, 2
            except IndexError:
                logging.info("Could not return two words")
                try:
                    words = re.findall(ONE_WORD_PATTERN, sentence)[0]
                    return words, 1
                except IndexError:
                    logging.info("Could not return one word")
                    return None, 0

    # formats the completion the way we want it
    def remove_first_words(self, sentence, amount):
        return ' '.join(sentence.split(' ')[amount:])

    # capitalizes after ponctuation. Also adds a period if
    # the sentence ends without ponctuation and
    # removes bad ponctuations
    def upper_after_ponc(self, sentence):
        # print("Processing ponctuation of:\n{}".format(sentence))
        split_with_punctuation = PUNC_FILTER.split(sentence)
        cased = ''.join([i.capitalize() for i in split_with_punctuation])
        if len(re.findall(QUOTE_PATTERN, cased)) % 2 == 1:
            # print("Número par de aspas")
            cased = re.sub(QUOTE_PATTERN, "", cased)
        if cased[-1] == ",":
            cased = cased[:-1] + "."
        elif cased[-1] not in ["?", "!", "."]:
            cased = cased + "."
        # print("Ponctuated sentence is:\n{}".format(cased))
        return cased

    # limit_use exists so when we use the one word model (bad)
    # we can limit how big its part is
    def complete_with_model(self, ending, model, amount, limit_use=False):
        completion = None
        try:
            tries = 0
            while completion is None or (limit_use and len(completion) > 30):
                if tries > 3:
                    break
                logging.info("We have this value for the ending:"
                             " \"%s\", AMOUNT = %s" % (ending, amount))
                completion = model.make_sentence_with_start(ending)
                logging.info("We have obtained this completion "
                             "inside complete_with_model:"
                             " \"%s\". The condition for loop is %s" % (
                                    completion, completion is None or
                                    (limit_use and len(completion) > 30)))
                tries += 1
            # no use to continue if we didn't get a result
            if completion is None:
                return None
            if len(completion) < config.MIN_LEN:
                # the later part aways uses model3
                addition = None
                while addition is None:
                    addition = self.models['model3'].make_sentence()
                completion += " " + addition
            logging.info("We obtained the completion \" % s\"" %
                         completion)
            cased = self.upper_after_ponc(completion)
            return "..." + self.remove_first_words(cased, amount)
        except KeyError:
            return None

    # This return a completion if one of the models
    # can handle the sentence and None if not
    def complete_sentence(self, sentence):
        ending, amount = self.get_last_words(sentence)
        logging.info("\nEnding:{}\nAmount:{}".format(ending, amount))

        if amount == 3:
            completion = self.complete_with_model(ending,
                                                  self.models['model3'], 3)
            if completion is not None:
                return completion
            amount = 2
            ending = self.remove_first_words(ending, 1)
        if amount == 2:
            completion = self.complete_with_model(ending,
                                                  self.models['model2'], 2)
            logging.info("We achieved the following completion "
                         "on 2 words:\n{}".format(completion))
            if completion is not None:
                return completion
            if ending.split(" ")[-1] in ["and", "or", "is",
                                         "was", "were", "for"]:
                amount = 1
                ending = self.remove_first_words(ending, 1)
        if amount == 1:
            completion = self.complete_with_model(
                ending, self.models['model1'], 1, True)
            logging.info("We achieved the following completion "
                         "on 1 word:\n{}".format(completion))
            if completion is not None:
                return completion
        return None

    # factories for common handlers
    @staticmethod
    def get_star_wars_handler():
        handler = \
            Handler({'model1': 'starwars 1 pos.json',
                     'model2': 'starwars 2 pos.json',
                     'model3': 'starwars 3 pos.json'})
        return handler

    @staticmethod
    def get_sando_handler():
        handler = \
            Handler({'model1': 'sando 1 pos.json',
                     'model2': 'sando 2 pos.json',
                     'model3': 'sando 3 pos.json'})
        return handler

    @staticmethod
    def get_asoiaf_handler():
        handler = \
            Handler({'model1': 'asoiaf 1 pos.json',
                     'model2': 'asoiaf 2 pos.json',
                     'model3': 'asoiaf 3 pos.json'})
        return handler

    @staticmethod
    def get_rosa():
        handler = \
            Handler({'model1': 'rosa 1 mark.json',
                     'model2': 'rosa 2 mark.json',
                     'model3': 'rosa 3 mark.json'}, pos=False)
        return handler

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


def run(sub_name, handler):
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

                completion = handler.complete_sentence(comment.body)
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


def run_handler(handler, sub_name):
    try:
        logging.info("Running handler on {}.".format(sub_name))
        run(sub_name, handler)
    except Exception as e:
        logging.critical(e, exc_info=True)
