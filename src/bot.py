import praw
import config
import logging
import datetime


logging.basicConfig(filename="log.log", level=logging.INFO,
                    filemode="w")
# logging.basicConfig(level=logging.INFO)

##################################################################
##################################################################
##################################################################


def custom_reply_to_reply(reply):
    reply.reply("COMMENT")


def login():
    logging.info("Logging in...")
    reddit = praw.Reddit(username=config.user,
                         password=config.password,
                         client_id=config.client_id,
                         client_secret=config.client_secret,
                         user_agent="sandocomplete")
    logging.info("Logged!")
    return reddit


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


# deletes comments with negative karma
def delete_bad_comments(reddit):
    user_comments = reddit.user.me().comments.new(limit=10)
    for comment in user_comments:
        if comment.score < 1:
            logging.info("Deleted a comment.")
            comment.delete()


def run_on_a_sub(sub_name, model):
    logging.info(datetime.datetime.now())

    replied_comments = []
    reddit = login()

    logging.info("Deleting bad replies...")
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

    logging.info(config.LINE +
                 "The replies in this run:")
    for comment in replied_comments:
        logging.info("{}\n{}\n{}\n{}".format(config.LINE, comment[0],
                                             comment[1], comment[2]))
