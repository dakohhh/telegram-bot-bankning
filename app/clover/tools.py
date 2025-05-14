from agents import function_tool

@function_tool
def send_money(account_number: str, amount: int,  bank:  str) -> bool:
    """ Send/Transfers money to a bank acount """
    print("Sent  money to user")

    return True