from fastapi import APIRouter, Request
import os
from fastapi.templating import Jinja2Templates


router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


TEXTS = {
    "happy": """It was a typical Saturday morning for Sarah - laundry, breakfast, and a bit of gardening. She had given up hope of seeing her brother, Jack, anytime soon; he was still deployed overseas, and his return was uncertain.

As she watered the plants, she heard the doorbell ring. She wiped her hands on her apron and headed to the front door, expecting it to be a neighbor or perhaps a delivery. But as she opened it, her heart skipped a beat.

There, standing on her porch with a huge smile and a bouquet of flowers, was Jack. He had managed to get leave and surprise her on her birthday.

"Jack!" Sarah exclaimed, her voice trembling with joy. She flung her arms around him, tears of happiness streaming down her face.

"Surprise! I couldn't miss your special day," Jack said, hugging her tightly. "I wanted to make it unforgettable."

As they hugged, Sarah felt a rush of love and gratitude. This was the best birthday surprise she could have ever asked for.

Together, they stepped inside, ready to celebrate and make the most of their time together. The day was filled with laughter, stories, and cherished moments that would stay with Sarah forever.
""",
    "sad": """The doctor's face said it all. No words. Just quiet, devastating truth.

"How long?" she asked, barely breathing.

"A day. Maybe two."

She sat beside the bed. His frail fingers twitched in hers.

"Mom?" His voice - soft, scared, still hers.

"I'm here, sweetheart."

"I don't wanna go."

Tears slipped down her cheeks, landing on his hand. She forced a smile. "You're not going anywhere alone, my love. I'll be right here."

A long silence. A deep sigh. His tiny chest rising, falling—then not rising again.

A machine beeped once. Then stopped.

She pressed her lips to his forehead, rocking gently.

"Sleep now, baby. Mommy loves you."

The world shattered.""",
}

QUESTIONS = {
    "happy": {
        "Q1": {
            "question": "Which of the following scenarios depicts the same emotion as Sarah's at the beginning of the text?",
            "options": {
                "A": "A student eagerly awaiting college acceptance letters, checking the mailbox daily",
                "B": "An elderly woman tending to her garden, reminiscing about her late husband",
                "C": "A child excitedly preparing for their first day of school",
                "D": "A job seeker submitting applications, feeling hopeful but resigned to a long wait",
            },
        },
        "Q2": {
            "question": "Which of these details from the text most strongly suggests that Jack's visit was completely unexpected?",
            "options": {
                "A": "Sarah was doing laundry when Jack arrived",
                "B": "Sarah was wearing an apron when she answered the door",
                "C": "Jack brought a bouquet of flowers",
                "D": "Sarah had given up hope of seeing Jack anytime soon",
            },
        },
        "Q3": {
            "question": "Which of the following best represents Sarah's emotional journey throughout the passage?",
            "options": {
                "A": "From excitement to disappointment",
                "B": "From contentment to anxiety",
                "C": "From resignation to elation",
                "D": "From frustration to relief",
            },
        },
        "Q4": {
            "question": "Why was Sarah's voice trembling when she saw Jack?",
        },
        "Q5": {
            "question": "What is the significance of the non-verbal communication in the extract?",
        },
    },
    "sad": {
        "Q1": {
            "question": "The child's line \"I don't wanna go\" implies he:",
            "options": {
                "A": "Fears abandonment by his mother",
                "B": "Associates death with physical departure",
                "C": "Mistrusts the doctor's prognosis",
                "D": "Resists medical treatment",
            },
        },
        "Q2": {
            "question": 'The line "The world shattered" functions as a metaphor for:',
            "options": {
                "A": "The mother's auditory hallucination post-death",
                "B": "The collapse of the mother's emotional universe",
                "C": "The doctor's failure to save the child",
                "D": "The destruction of hospital equipment",
            },
        },
        "Q3": {
            "question": 'The words "soft, scared" (child\'s voice) and "forced a smile" (mother\'s action) together highlight:',
            "options": {
                "A": "The disparity between vulnerability and performative comfort",
                "B": "The child's physical weakness",
                "C": "The mother's emotional detachment",
                "D": "The doctor's professional demeanor",
            },
        },
        "Q4": {
            "question": 'What does the mother mean by "You\'re not going anywhere alone"?',
        },
        "Q5": {
            "question": "What is the significance of the non-verbal communication in the extract?",
        },
    },
}


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/record")
async def get_record(request: Request, name: str, text: str):
    if text.lower() not in TEXTS:
        return "Invalid text type"

    return templates.TemplateResponse(
        "record.html",
        {
            "request": request,
            "name": name,
            "text": TEXTS[text.lower()],
            "key": text,
            "questions": QUESTIONS[text.lower()],
        },
    )
