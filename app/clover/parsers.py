import base64
from io import BytesIO
from openai import OpenAI
from typing import Union
from functools import lru_cache
from ..settings import settings
from abc import ABC, abstractmethod
from .models.inputs import TransferMoneyInput
from .models.checks import BankCodeCheck

ParserFileDataTypes = Union[bytes, BytesIO]
class BaseParser(ABC):
    
    @abstractmethod
    def parse(self):
        raise NotImplementedError("Subclass call must be inherited")
    


class BankCodeParser(BaseParser):

    @lru_cache(100)
    def parse(self, bank_name: str, data: str):
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"""From the following text, extract the numeric bank code specifically for the bank named: {bank_name}. 
                Important instructions:
                - Only return the numeric bank code for {bank_name}.
                - Do NOT trim or remove any leading zeros (e.g., return '057', not '57').
                - The output must be **only** the code (no explanation or extra text).
                - Do not return any unrelated numbers (e.g., account numbers or phone numbers).
                Text:
                {data}
                """
            }
            ],
            response_format=BankCodeCheck,
        )

        return response.choices[0].message.parsed

    

class TransferMoneyParser(BaseParser):
    """Base parser for transfer money"""

    def parse(self):
        raise NotImplementedError(f"Subclass {self.__class__.__name__} call must be inherited")

class PhotoTransferMoneyParser(TransferMoneyParser):
    async def parse(self, data: ParserFileDataTypes ) -> TransferMoneyInput:

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        final_data = data

        if isinstance(data, BytesIO):
            final_data = data.getvalue()
        
        img_str = base64.b64encode(final_data).decode()

        response = client.beta.chat.completions.parse(
            model="gpt-4.1-mini",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract all the text from this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                ]}
            ],
            response_format=TransferMoneyInput,
            max_tokens=1000
        )

        return response.choices[0].message.parsed