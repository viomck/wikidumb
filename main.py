import discord
import json
import random
import requests
import secrets

common_words = ['the', 'of', 'and', 'a', 'to', 'in', 'is', 'be', 'that',
                'was', 'he', 'for', 'it', 'with', 'as', 'his', 'i', 'on',
                'have', 'at', 'by', 'not', 'they', 'this', 'had', 'are',
                'but', 'from', 'or', 'she', 'an', 'which']

client: discord.Client = discord.Client()
alpha = 'abcdefghijklmnopqrstuvwxyz'
do_copypasta = False

api_url = 'https://en.wikipedia.org/w/api.php?format=json'

search_url = api_url + '&action=opensearch' \
                       '&limit=1' \
                       '&namespace=0' \
                       '&redirects=resolve' \
                       '&search='

read_url = api_url + '&action=query' \
                     '&prop=extracts' \
                     '&explaintext=1' \
                     '&exintro=1' \
                     '&titles='

wikitext_url = api_url + '&action=parse&prop=wikitext&page='


def main() -> None:
    """
    Application entrypoint
    """
    client.run(get_config()['token'])


@client.event
async def on_message(message: discord.Message):
    global do_copypasta

    if message.author.bot:
        return

    force = message.author.id == get_config()['owner'] and \
            message.clean_content.startswith('wdforce')

    if random.randint(0, 99) > 0 and not do_copypasta and not force:  # 1/100 chance
        return

    do_copypasta = False

    content = message.clean_content.lower()
    words = list(filter(word_filter, content.split(' ')))

    copypasta = get_wikipedia_copypasta(words)

    if not copypasta:
        do_copypasta = True  # Try on next message
    else:
        mode = get_config()['mode']
        formatted_copypasta = ''

        if mode == 'AB':
            if message.guild.id in get_config()['ab_guilds']:
                mode = secrets.choice(['SENTENCE', 'LEGACY'])
                formatted_copypasta = '(' + mode[0] + ') ' + formatted_copypasta
            else:
                mode = get_config()['ab_backup']

        if mode == 'SENTENCE':
            formatted_copypasta += copypasta.split('. ')[0]
        elif mode == 'LEGACY':
            formatted_copypasta += copypasta

        await message.channel.send(formatted_copypasta[:2000])


@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game('git.io/wikidumb'))


def get_wikipedia_copypasta(words: list, tries: int = 0):
    """
    Returns a Wikipedia copypasta for a given word list. Will try and pick a
    random word to get a copypasta for.

    :param words: Word list
    :param tries: Internal parameter - don't set!
    :return: A Wikipedia copypata, or None if none can be found
    """
    if tries == 5 or not words:
        return None

    word = random.choice(words)
    words.remove(word)

    article = get_article_for_query(word)
    word_clean = clean_word(word)
    article_clean = clean_word(article)

    if word_clean != article_clean:
        return get_wikipedia_copypasta(words, tries + 1)

    para = get_first_para_from_article(article)

    if 'may refer to' in para:
        next_article = get_first_link_in_article(article)
        next_article_clean = clean_word(next_article)

        # Be a bit more lax on disambiguation, but still enforce relevance
        if not next_article_clean.startswith(word_clean):
            return get_wikipedia_copypasta(words, tries + 1)

        para = get_first_para_from_article(next_article)

    return para


def get_first_para_from_article(article: str):
    print('get_first_para_from_article: ' + article)

    # Pages is a dict of page IDs to objects
    raw = requests.get(read_url + article).json()
    pages = raw['query']['pages']
    text = list(pages.items())[0][1]['extract']

    if 'may refer to' in text:
        return text

    return text.split('\n')[0]


def get_first_link_in_article(article: str):
    print('get_first_link_in_article: ' + article)

    raw = requests.get(wikitext_url + article).json()
    text = raw['parse']['wikitext']['*']

    if 'may refer to' in text:
        text = text.split('may refer to')[1]

    link = text.split('[[')[1].split(']]')[0]

    return link


def get_article_for_query(query: str) -> str:
    print('get_article_for_query: ' + query)
    return requests.get(search_url + query).json()[1][0]


def clean_word(word: str) -> str:
    word = word.lower()
    out = ''

    for _, c in enumerate(word):
        if c in alpha:
            out += c

    return out


def word_filter(word: str) -> bool:
    """
    Filters words to make them more Wikipedia friendly
    :param word: Word to filter
    :return: OK
    """
    if word in common_words:
        return False

    for _, c in enumerate(word):
        if c not in alpha:
            return False
    return True


def get_config() -> dict:
    """
    Loads config from disk
    :return: Config dict
    """
    with open('config.json', 'r') as file:
        config = json.load(file)
        return config


if __name__ == '__main__':
    main()
