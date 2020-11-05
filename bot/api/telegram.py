import emoji
import requests
import Levenshtein as lev

import bot.api.keys


class TelegramIO():
    def __init__(self, persistence, commands):
        """Inits the Telegram-Interface
        """
        self.base_url = "https://api.telegram.org/bot" + bot.api.keys.telegram_api + "/"
        self.persistence = persistence
        self.commands = commands
        # Dynamic variables for answering
        self.chat_id = ""
        self.offset = 0
        self.message_id = ""



    def update_commands(self,commands):
        self.commands = commands

    ########################################################################
    """Helper-Functions"""


    def fetch_updates(self):
        """"""
        update_url = self.base_url + "getUpdates"
        data = {"offset":self.offset}

        try:
            result = requests.post(update_url,data=data)
            result = result.json()["result"]
        except:
            result = ""

        return result


    def handle_result(self, result):
        """Inspects the message and reacts accordingly. Can easily be extended"""
        message_data = result[0]

        self.persistence.increment("messages_read")
        self.offset = message_data["update_id"] + 1

        if "edited_message" in message_data:
            return "nothing", "happened"

        message = message_data["message"]
        self.message_id = message["message_id"]
        self.chat_id = message["chat"]["id"]
        author = message["from"]

        chat_members = self.persistence.read("chat_members")
        if str(author["id"]) not in chat_members:
            name = ""
            if "first_name" in author:
                name += author["first_name"] + " "
            if "last_name" in author:
                name += author["last_name"]
            if len(name) == 0:
                name += "anonymous"
            chat_members[author["id"]] = name
            self.persistence.write("chat_members", chat_members)
            self.send_message("Welcome to this chat " + name + "!")

        if "text" in message:
            print("Chat said: ", emoji.demojize(message["text"]))

            if "entities" in message:
                for entry in message["entities"]:
                    if entry["type"] == "bot_command":
                        return self.handle_command(message["text"][1:])

        elif "photo" in message:
            print("Photo received, what do I do?")

        return "nothing", "happened"


    def handle_command(self, command):
        """Handles commands and stuff, using a bash-like syntax:
        /[command] [argument 1] [argument 2] ...
        """
        full = command.split(" ")
        command = self.fuzzy_match_command(full[0])
        if len(command) != 1:
            if command[0] == "EXACT":
                self.persistence.increment("commands_executed")
                return command[1], full[1:]
            else:
                send = "Did you mean <code>" + command[1] + "</code>"
                for i in range(2,len(command)):
                    send += " or <code>" + command[1] + "</code>"
                send += "?"
                self.send_message(send)
        else:
            self.send_message("Command <code>" + full[0] + "</code> not found. Please try again.")

        return "nothing", ["happened"]


    def fuzzy_match_command(self, input):
        matches = ["not exact"]
        for command in self.commands.keys():
            if lev.ratio(input.lower(),command) > 0.8:
                matches.append(command)
                if lev.ratio(input.lower(),command) == 1:
                    return ["EXACT", command]

        return matches


    def send_thinking_note(self):
        data = {
            "chat_id" : self.chat_id,
            "action" : "typing",
        }
        send_url = self.base_url + "sendChatAction"
        try:
            r = requests.post(send_url, data=data)
        except:
            print("Could not show that I'm thinking =(")


    def send_message(self, message):

        if message == "":
            return

        print("SENDING: " + emoji.demojize(message))

        data = {
            'chat_id': self.chat_id,
            'text': emoji.emojize(message),
            "parse_mode": "HTML",
            "reply_to_message_id" : self.message_id,
        }

        send_url = self.base_url + "sendMessage"
        try:
            r = requests.post(send_url, data=data)
            print(r.status_code)
            self.persistence.increment("messages_sent")
        except:
            out = datetime.datetime.now().strftime("%d.%m.%y - %H:%M")
            out += " @ " + "telegram.send_message"
            out += " --> " + "did not send:\n" + message
            self.persistence.append_list("log", out)


    def send_photo(self, url, caption):
        print("SENDING PHOTO: " + url)
        data = {
            'chat_id': self.chat_id,
            'photo': url,
            "parse_mode": "HTML",
            "reply_to_message_id" : self.message_id,
            'caption' : caption,
        }
        send_url = self.base_url + "sendPhoto"
        try:
            r = requests.post(send_url, data=data)
            self.persistence.increment("photos_sent")
        except:
            out = datetime.datetime.now().strftime("%d.%m.%y - %H:%M")
            out += " @ " + "telegram.send_photo"
            out += " --> " + "did not send:\n" + url
            self.persistence.append_list("log", out)
