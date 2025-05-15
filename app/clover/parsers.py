import base64
from abc import ABC, abstractmethod
from openai import OpenAI
from ..settings import settings
from .models.inputs import TransferMoneyInput
from ..common.utils.helpers import load_file_to_memory
class BaseParser(ABC):
    
    @abstractmethod
    def parse(self):
        raise NotImplementedError("Subclass call must be inherited")

class TransferMoneyParser(BaseParser):
    """Base parser for transfer money"""

    def parse(self):
        raise NotImplementedError(f"Subclass {self.__class__.__name__} call must be inherited")

class PhotoTransferMoneyParser(TransferMoneyParser):
    async def parse(self, data: bytes ) -> TransferMoneyInput:

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        img_str = base64.b64encode(data).decode()

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