import onnxruntime_genai as og
import argparse
import time
import os
import sys

class Phi3Model:
    
    def __init__(self, max_length = 2048) -> None:
        if os.path.exists("./cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4"):
            self.model = og.Model('cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4')
            self.tokenizer = og.Tokenizer(self.model)
            print("Successful Loading Model!")
        else:
            print("Pls download Phi model")
            sys.exit(1)
            
        self.search_options = {"max_length" : max_length}
        self.chat_template = '<|user|>\n{{input}} <|end|>\n<|assistant|>'
    
    def search(self, text):
        prompt = self.chat_template.replace("{{input}}", text)
        input_tokens = self.tokenizer.encode(prompt)
        params = og.GeneratorParams(self.model)
        params.set_search_options(**self.search_options)
        params.input_ids = input_tokens
        generator = og.Generator(self.model, params)
        new_tokens = []
        while not generator.is_done():
            generator.compute_logits()
            generator.generate_next_token()
            new_token = generator.get_next_tokens()[0]
            new_token = self.tokenizer.decode(new_token)
            new_tokens.append(new_token)
        return "".join(new_tokens)
        
if __name__ == "__main__":
    phi3_model = Phi3Model()
    print(phi3_model.search("why earth is sphere ?"))