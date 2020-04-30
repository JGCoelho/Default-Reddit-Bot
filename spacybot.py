import markovify
import re
import json
import spacy
import logging
nlp = spacy.load('en')


class MarkovPT(markovify.Text):
    def word_split(self, sentence):
        return ["::".join((word.orth_, word.pos_)) for word in nlp(sentence)]

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence


def save_model_as_json(text_model, file_name):
    model_json = text_model.to_json()
    with open('models\\' + file_name + '.json', 'w') as outfile:
        json.dump(model_json, outfile)


def load_model_from_json(file_name):
    logging.info("Opening model: {}".format(file_name))
    with open('models\\' + file_name + '.json') as json_file:
        return MarkovPT.from_json(json.load(json_file))


def model_and_save(file_name, state_size=4):
    # also returns the model
    with open('samples\\' + file_name + '.txt', encoding="utf-8") as file:
        model = MarkovPT(file.read(), state_size=state_size)
    save_model_as_json(model, file_name)
    return model


def get_crypto():
    return load_model_from_json("Crypto")


################################################################
# Methods for creating the messages
################################################################
flawed_utf_patt = re.compile(r'\\x\.*')
quote_patt = re.compile("\"")
space_patt = re.compile(r'\s+')
nt_patt = re.compile(r'\s+n\'t')
s_patt = re.compile(r'\s+\'s')
nt_patt2 = re.compile(r'\s+n’t')
s_patt2 = re.compile(r'\s+’s')


def format_msg(msg):
    msg = re.sub(space_patt, " ", msg)
    msg = re.sub(flawed_utf_patt, "", msg)
    msg = re.sub(quote_patt, "", msg)
    msg = re.sub(nt_patt, "n't", msg)
    msg = re.sub(s_patt, "'s", msg)
    msg = re.sub()
    msg = re.sub(u'\\s([?\\.\'!,;"](?:\\s|$))', r'\1', msg)
    return msg


def make_message(model):
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
    entire_sentence = format_msg(entire_sentence)
    return entire_sentence


def test():
    msg = "ca n't is n't it 's that 's"
    print(format_msg(msg))
    model = get_crypto()
    for i in range(5):
        print(make_message(model))


test()
