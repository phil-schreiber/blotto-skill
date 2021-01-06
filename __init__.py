# Blotto - master of glue code

from google.cloud import translate_v2 as translate
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from mycroft.util.parse import match_one
import requests

translate_client = translate.Client()

class ButtonValidator:
    def __init__(self, values, threshold):
        self.values = values
        self.threshold = threshold

    def validate(self, utterance):
        best = match_one(utterance, self.values)
        return best[1] > self.threshold


class BlottoSkill(MycroftSkill):
    button_match_threshold = 0.6
    button_attempts_max = 3

    # The constructor of the skill, which calls MycroftSkill's constructor
    def __init__(self):
        super(BlottoSkill, self).__init__(name="BlottoSkill")
        self.conversation_active = False
        self.blotto_host = "http://796784407dd4.ngrok.io/"
        self.append_endpoint = (
            self.blotto_host + "interact"
        )        

    @intent_handler(IntentBuilder("").require("BlottoOtto"))
    def handle_talk_to_blotto_intent(self, message):
        response = self.get_response("connecting.to.blotto")
        self.conversation_active = True
        while response is not None and self.conversation_active:
            messages = self.fetch_blotto_response(response)            
            if len(messages) > 1:
                resp = translate_client.translate(messages, target_language='DE', source_language='EN')                
                self.speak(resp['translatedText'])
            if len(messages) == 0:
                messages = ["no response from blotto"]
            response = self.handle_final_output(messages[-1])

        self.speak("disconnecting from blotto")

    def handle_final_output(self, message, attempts=0):
        if attempts > self.button_attempts_max:
            return None
        if attempts > 0:
            self.speak("You can also say Option 1, Option 2, etc")
        # if we have buttons, handle them
        if "buttons" in message:
            # speak the text on the message
            self.speak(message["text"])

            buttons = message["buttons"]
            button_titles = [b["title"] for b in buttons]

            if len(buttons) == 1:
                # if we have a single button, assume it's a confirmation
                self.speak("To confirm, say")
            elif len(buttons) > 1:
                # if we have many buttons, list the options
                self.speak("You can say")
            # read out our button title options, separated by "Or"
            for button in buttons[:-1]:
                self.speak(button["title"])
                self.speak("Or")
            # read the final button option, and await a response
            # that is in the list of what we just returned OR
            # is "option 1", "option 2", ..., "option N"  N
            option_list = [f"option {i+1}" for i in range(len(buttons))]
            validation_options = button_titles + option_list
            button_validator = ButtonValidator(
                validation_options, self.button_match_threshold
            )
            print(f"trying attempt {attempts}")
            response = self.get_response(
                button_titles[-1],
                validator=button_validator.validate,
                num_retries=0,
                on_fail=self.on_failed_button,
            )
            print(f"response {response}")
            # if response is not None, we passed the validator
            if response is not None:
                best_match = match_one(response, validation_options)
                response = best_match[0]
                best_ind = validation_options.index(response)
                if best_ind >= len(buttons):
                    best_ind = best_ind % len(buttons)
                response = buttons[best_ind]["payload"]
                return response
            return self.handle_final_output(message, attempts=attempts + 1)
        # if we don't have buttons, just get_response
        return self.get_response(message, num_retries=0)

    def on_failed_button(self, utt):
        return "Was sagst du da?"

    def fetch_blotto_response(self, utterance):
        if "stop" in utterance.lower():
            self.conversation_active = False
            return [{"text": "Schüps"}]
        messages = self.hit_blotto(utterance)
        print(messages)
        return messages

    def stop(self):
        self.conversation_active = False

    def hit_blotto(self, utterance):
        resp = translate_client.translate(utterance, target_language='EN', source_language='DE')
        print(f"sending {resp['translatedText']} to {self.append_endpoint}")
        append_response = requests.post(
            self.append_endpoint, data=resp['translatedText']
        )
       
        return append_response.json().get('text')


def create_skill():
    return BlottoSkill()
