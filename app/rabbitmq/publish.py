from .client import RabbitMQClient

def main():
    url = "amqp://user:pass@localhost:5672"
    
    deposit = {
        "amount": 4000,
        "user_id": "wee"
    }

    notification = {
        "user_id": "wee",
        "status": "success"
    }
    
    client = RabbitMQClient(url)
    
    # Ensure the exchange exists
    client.declare_exchange("charge")
    
    # Publish message
    client.publish("charge", "charge.deposit", deposit)
    client.publish("charge", "charge.notification", notification)
    print(f"Published message: {deposit}")
    print(f"Published message: {notification}")
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    main()