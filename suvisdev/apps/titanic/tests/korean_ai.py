import ollama
from kiwipiepy import Kiwi

kiwi = Kiwi()


def run_korean_ai(user_text: str) -> str:
    cleaned_text = kiwi.join(kiwi.tokenize(user_text))

    tokens = kiwi.tokenize(cleaned_text)
    nouns = [t.form for t in tokens if t.tag.startswith('NN')]
    print(f"추출된 핵심 명사: {nouns}")

    response = ollama.chat(
        model='anpigon/eeve-korean-10.8b:latest',
        messages=[{'role': 'user', 'content': cleaned_text}]
    )
    return response['message']['content']
