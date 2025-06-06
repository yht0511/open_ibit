import transformers
import os

def count_tokens(str):
    result = tokenizer.encode(str)
    return len(result)


chat_tokenizer_dir = os.path.dirname(os.path.abspath(__file__))


tokenizer = transformers.AutoTokenizer.from_pretrained( 
        chat_tokenizer_dir, trust_remote_code=True
        )
