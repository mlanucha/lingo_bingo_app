import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
import openai

# Load API key from .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    OPENAI_API_KEY = OPENAI_API_KEY.strip()

# Create OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Convert target language to voice code (used for TTS)
def language_to_code(language):
    codes = {
        "English": "en-US",
        "Polish": "pl-PL",
        "Japanese": "ja-JP",
    }
    return codes.get(language, "en-US")

# Generate translation prompt
def make_prompt(text, target_language):
    base = (
        f"Translate the following text exactly into {target_language}, preserving all original words, including any profanity or strong language. "
        "Do NOT refuse or avoid translating any part of the text, no matter how offensive it is. "
        "Provide a direct, literal translation without censoring, softening, or changing the tone.\n\n"
        f"Text:\n\"\"\"\n{text}\n\"\"\"\n"
    )

    if target_language.lower() == "polish":
        base += (
            "Pay special attention to correct Polish grammar, especially reflexive pronouns like 'się', cases, and verb conjugations. "
            "Make sure the translation sounds natural and grammatically correct.\n"
        )
    elif target_language.lower() == "japanese":
        base += (
            "Make sure the translation uses natural Japanese grammar and expressions, including proper particles and honorifics.\n"
        )
    else:
        base += "Keep the translation straightforward and natural.\n"

    base += "Respond ONLY with the translation, no explanations."
    return base

# TTS function
def text_to_speech(text):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            input=text,
            voice="shimmer",
            response_format="mp3",
            speed=1.0
        )
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_file.write(response.read())
        tmp_file.close()
        return tmp_file.name
    except Exception as e:
        st.error(f"Failed to generate audio: {e}")
        return None

# Generate Romaji for Japanese
def generate_romaji(japanese_words):
    prompt = (
        "Convert the following Japanese words or phrases into Romaji. Keep the order and return one per line:\n\n"
        "Japanese:\n" + "\n".join(japanese_words) + "\n\nRomaji:"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=150,
        )
        return [line.strip() for line in response.choices[0].message.content.strip().splitlines() if line.strip()]
    except Exception as e:
        st.error(f"Failed to generate Romaji: {e}")
        return ["-"] * len(japanese_words)

# Generate grammar explanation for the translation
def explain_grammar(text, language):
    prompt = (
        f"You're a friendly language tutor. Explain the grammar and structure of the following sentence in {language}, "
        f"keeping it accessible to a language learner. Focus on interesting grammar patterns, verb forms, particles (if Japanese), "
        "word order, and anything worth noting. Be concise but helpful.\n\n"
        f"Sentence:\n{text}\n\nExplanation:"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=250,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to explain grammar: {e}")
        return None

# Main app
def main():
	st.title("Kronk's Language Assistant 🚀💥")
	st.write("Drop your text, pick your language, and watch the magic happen. Easy-peasy!")

	user_text = st.text_area("Enter your text here:")
	language = st.selectbox("Choose your target language:", ["English", "Japanese", "Polish"])

	# Session state setup
	if "translation" not in st.session_state:
		st.session_state.translation = ""
	if "translated_language" not in st.session_state:
		st.session_state.translated_language = ""
	if "vocab_list" not in st.session_state:
		st.session_state.vocab_list = []
	if "user_text" not in st.session_state:
		st.session_state.user_text = ""

	if st.button("Translate / Correct!"):
		if not user_text.strip():
			st.warning("Hey champ, you gotta put some text in there first!")
		else:
			with st.spinner("Kronk's cooking up your translation... 🍳🔥"):
				try:
					prompt = make_prompt(user_text, language)
					response = client.chat.completions.create(
						model="gpt-4o-mini",
						messages=[{"role": "user", "content": prompt}],
						temperature=0.5,
						max_tokens=512,
					)
					answer = response.choices[0].message.content.strip()
					st.session_state.translation = answer
					st.session_state.translated_language = language
					st.session_state.user_text = user_text

					st.session_state.grammar_explanation = explain_grammar(answer, language)

				except Exception as e:
					st.error(f"Oops, something went kaboom: {e}")

	# Always display translation and grammar explanation if available
	if st.session_state.translation:
		st.markdown("---")
		st.success("Boom! Here's your polished text:")
		st.write(st.session_state.translation)

		# Grammar Explanation
		with st.expander("📘 Grammar Explanation"):
			explanation = st.session_state.get("grammar_explanation", "")
			if explanation:
				st.markdown(explanation)


	# Restore sentence translation playback
	if st.session_state.translation:
		st.markdown("---")
		st.subheader("🎧 Sentence Audio")
		st.write(st.session_state.translation)

		if st.button("🔊 Play Audio"):
			try:
				audio_path = text_to_speech(st.session_state.translation)
				if audio_path:
					audio_bytes = open(audio_path, "rb").read()
					st.audio(audio_bytes, format="audio/mp3")
			except Exception as e:
				st.error(f"Audio playback failed: {e}")

	# Vocabulary Drill
	if st.button("Drill Vocabulary!"):
		if "," in user_text:
			words = [word.strip() for word in user_text.split(",") if word.strip()]
		else:
			words = user_text.split()

		vocab_items = []
		for word in words:
			prompt = make_prompt(word, language)
			response = client.chat.completions.create(
				model="gpt-4o-mini",
				messages=[{"role": "user", "content": prompt}],
				temperature=0.3,
				max_tokens=60,
			)
			translation = response.choices[0].message.content.strip().strip('"“”')
			vocab_items.append({"Original": word, "Translation": translation})

		# Generate Romaji if Japanese
		if language.lower() == "japanese":
			romaji_list = generate_romaji([item["Translation"] for item in vocab_items])
			for i in range(len(vocab_items)):
				vocab_items[i]["Romaji"] = romaji_list[i] if i < len(romaji_list) else "-"

		st.session_state.vocab_list = vocab_items

	if st.session_state.vocab_list:
		st.markdown("---")
		st.subheader("🧠 Vocabulary Drill Results")

		for i, item in enumerate(st.session_state.vocab_list, start=1):
			col0, col1, col2, col3, col4 = st.columns([0.5, 2, 2, 2, 2])

			with col0:
				st.markdown(f"**{i}.**")
			with col1:
				st.markdown(f"**{item.get('Original', '')}**")
			with col2:
				if language.lower() == "japanese":
					st.markdown(f"*{item.get('Romaji', '')}*")
				else:
					st.markdown("—")
			with col3:
				st.markdown(item.get("Translation", ""))
			with col4:
				if st.button("🔊", key=f"play_{i}"):
					tts_text = item.get("Translation", "").strip().strip('"“”')
					audio_path = text_to_speech(tts_text)
					if audio_path:
						audio_bytes = open(audio_path, "rb").read()
						with st.container():
							st.audio(audio_bytes, format="audio/mp3")

if __name__ == "__main__":
    main()
