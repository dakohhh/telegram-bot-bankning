import pika
import pika.channel
import pika.spec
from .client import RabbitMQClient, Queue

def on_charge_deposit(ch: pika.channel.Channel,
                      method: pika.spec.Basic.Deliver,
                      properties: pika.spec.BasicProperties,
                      body: bytes) -> None:
    print("Processing order:", body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_charge_notification(ch: pika.channel.Channel,
                      method: pika.spec.Basic.Deliver,
                      properties: pika.spec.BasicProperties,
                      body: bytes) -> None:
    print("Processing notification:", body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    url = "amqp://user:pass@localhost:5672"
    client = RabbitMQClient(url)
    
    # Ensure the exchange exists
    client.declare_exchange("charge")
    
    # Declare queue
    queue = client.declare_queue("charge_deposit")
    queue_name = queue.method.queue


    queue = client.declare_queue("charge_notification")
    queue_name_2 = queue.method.queue
    
    # Bind queue to exchange with routing key
    client.bind_queue(queue_name, exchange="charge", routing_key="charge.deposit")
    client.bind_queue(queue_name_2, exchange="charge", routing_key="charge.notification")
    
    # Create queue object for subscription
    queue_obj = Queue(name=queue_name, callback=on_charge_deposit)
    queue_obj_2 = Queue(name=queue_name_2, callback=on_charge_notification)
    
    try:
        client.subscribe(queues=[queue_obj, queue_obj_2])
    except KeyboardInterrupt:
        client.close()

if __name__ == "__main__":
    main()