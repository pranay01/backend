from flask import jsonify, abort
import os
import replicate
import time
from typing import Generator

from src.constants import banned_words, mocked_urls


def create_generator(prompt: str) -> Generator:
    LOCAL_ENVIRONMENT = os.environ.get('LOCAL_ENVIRONMENT')
    # If ENV does not exist, assume this is production and reach out to
    # replicate servers; otherwise, use a mocked out version of replicate's
    # models prediction service.
    if LOCAL_ENVIRONMENT is None:
        model = replicate.models.get("laion-ai/erlich")
        try:
            version = model.versions.get("06c5e3584e1c0dc65965826bd0c92a28f496efd7144661b7ac1bc48bfde6ce4c")
            return version.predict(prompt=prompt, batch_size=8)
        except Exception as e:
            print('An error has occured while calling model.predict')
            print(e)
    else:
        return mocked_urls_generator()


def is_prompt_permissible(prompt: str) -> bool:
    if any([banned_word in prompt for banned_word in banned_words]):
        return False
    else:
        return True


def json_abort(status_code, data=None):
    response = jsonify(data)
    response.status_code = status_code
    abort(response)


def mocked_urls_generator():
    time.sleep(0.5)
    for mocked_uri in mocked_urls:
        yield mocked_uri['uri']
        time.sleep(0.1)
