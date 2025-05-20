import json
import pika
import pika.adapters.blocking_connection
import pika.channel
import pika.spec
import aio_pika
from abc  import ABC, abstractmethod
from pika.exchange_type import ExchangeType
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union, Callable, Tuple, Generic, TypeVar

CallbackType = Callable[
    [pika.channel.Channel, pika.spec.Basic.Deliver, pika.spec.BasicProperties, bytes],
    None
]

AsyncCallbackType = Callable[[aio_pika.abc.AbstractIncomingMessage], Any]

T = TypeVar("T")

class QueueWrapper(BaseModel, Generic[T]):
    q: Union[str, aio_pika.abc.AbstractQueue]
    callback: Optional[T] = None
    callback_args: Optional[Tuple] = ()
    callback_kwargs: Optional[Dict] = {}

    model_config = {
        "arbitrary_types_allowed": True
    }


class BaseRabbitMQClient(ABC):
    def __init__(self, url: str):
        self.url = url
        self.connection: Optional[Union[pika.BlockingConnection, aio_pika.RobustConnection]] = None
        self.channel: Optional[Union[pika.adapters.blocking_connection.BlockingChannel, aio_pika.abc.AbstractChannel]] = None

    @abstractmethod
    def connect(self) -> None:
       ...


class RabbitMQClient(BaseRabbitMQClient):
    def connect(self):
        parameters = pika.URLParameters(self.url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel: pika.adapters.blocking_connection.BlockingChannel = self.connection.channel()
        
    def declare_exchange(self, name: str, exchange_type: str = ExchangeType.direct, durable: bool = True):
        if not self.channel:
            self.connect()
        self.channel.exchange_declare(exchange=name, exchange_type=exchange_type, durable=durable)
        
    def declare_queue(self, queue: str, durable: bool = True):
        if not self.channel:
            self.connect()
            
        return self.channel.queue_declare(queue=queue, durable=durable)
        
    def publish(self, exchange: str, routing_key: str, message: Union[BaseModel, Dict[str, Any]], properties: Optional[pika.BasicProperties]=None):
        if not self.channel:
            self.connect()
            
        if isinstance(message, BaseModel):
            message = message.model_dump()
        
        if not properties:
            # This is to make messages persistent in case of failure
            properties = pika.BasicProperties(delivery_mode=2)
        
        self.channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=properties
        )
    
    def bind_queue(self, queue: str, exchange: str, routing_key: str):
        if not self.channel:
            self.connect()
            
        self.channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key,
        )
    
    def subscribe(self, queues: List[QueueWrapper], auto_ack=False):
        if not self.channel:
            self.connect()
        
        for q in queues:
            self.channel.basic_consume(
                queue=q.name,
                on_message_callback=q.callback,
                auto_ack=auto_ack
            )
        
        print(f"[*] Waiting for messages from queues: {[q.name for q in queues]}")
        self.channel.start_consuming()
    
    def close(self):
        if self.connection:
            self.connection.close()
        self.channel = None
        self.connection = None
    

class AsyncRabbitMQClient(BaseRabbitMQClient):
    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()

    async def declare_exchange(self, exchange_name: str,*, exchange_type: aio_pika.ExchangeType = aio_pika.ExchangeType.DIRECT, durable: bool = True) -> aio_pika.abc.AbstractExchange:

        if not self.channel:
            await self.connect()

        exchange = await self.channel.declare_exchange(name=exchange_name, type=exchange_type, durable=durable)

        return exchange

    async def declare_queue(self, queue_name: str, *, durable: bool = True) -> aio_pika.abc.AbstractQueue:
        if not self.channel:
            self.connect()

        queue = await self.channel.declare_queue(name=queue_name, durable=durable)  
            
        return queue

    async def get_exchange(self, exchange_name: str) -> aio_pika.abc.AbstractExchange:
        if not self.channel:

            await self.connect()

        exchange = await self.channel.get_exchange(name=exchange_name)

        return exchange
    

    async def bind_queue(self, queue: aio_pika.abc.AbstractQueue, exchange: aio_pika.abc.AbstractExchange, routing_key: str):
        if not self.channel:
            await self.connect()
        
        await queue.bind(exchange, routing_key=routing_key)

    async def publish(
            self, 
            exchange: aio_pika.abc.AbstractExchange, 
            routing_key: str, 
            *, 
            message: Union[BaseModel, Dict[str, Any]], 
            headers: Optional[Dict] = None,  
            persistent: bool = True):
        if not self.channel:
            await self.connect()
        
        # Convert message to dict if it's a BaseModel
        if isinstance(message, BaseModel):
            message = message.model_dump()
        
        # Convert message to JSON and encode
        message_body = json.dumps(message).encode() if isinstance(message, dict) else message
        
        # Create message with persistence if needed
        message_obj = aio_pika.Message(
            body=message_body,
            headers=headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT if persistent else aio_pika.DeliveryMode.NOT_PERSISTENT
        )
        
        await exchange.publish(message_obj, routing_key=routing_key)


    async def subscribe(self, queues: List[QueueWrapper[AsyncCallbackType]], auto_ack=False):
        if not self.channel:
            await self.connect()
        
        consumers = []
        for q in queues:
            # Only start consuming if there exists a callback
            if q.callback:
                # Get the queue object or name
                queue_obj = q.q
                
                # If q.q is a string, we need to get the queue object
                if isinstance(queue_obj, str):
                    queue_obj = await self.channel.declare_queue(name=queue_obj)
                
                async def process_message(message: aio_pika.abc.AbstractIncomingMessage, callback=q.callback, callback_args=q.callback_args, callback_kwargs=q.callback_kwargs):
                    async with message.process(requeue=not auto_ack):
                        await callback(message, *callback_args, **callback_kwargs)
                
                # Start consuming
                consumer_tag = await queue_obj.consume(process_message)
                consumers.append((queue_obj, consumer_tag))
        
        queue_names = []
        for q in queues:
            if isinstance(q.q, str):
                queue_names.append(q.q)
            else:
                queue_names.append(q.q.name)
                
        print(f"[*] Waiting for messages from queues: {queue_names}")
        return consumers

