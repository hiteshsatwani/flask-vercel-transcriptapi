from flask import Flask, abort
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter
import os
from openai import OpenAI
import json
from dotenv import load_dotenv
from flask import request, jsonify
from werkzeug.utils import secure_filename
import ffmpeg
import whisper

load_dotenv()


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads/'
CORS(app)




sampleresp = {"messages": [{"role": "user", "content": "Summarize the content of this transcript in 250 words indetail giving information on each of the subtopics in the transcript: [\"Love is often described as heartwarming,\\nheart-wrenching and even heartbreaking.\", \"So, what does the brain have\\nto do with it?\", \"Everything!\", \"The journey from first spark to last tear\\nis guided by a symphony\", \"of neurochemicals and brain systems.\", \"As you begin to fall for someone,\", \"you may find yourself excessively\\ndaydreaming about them\", \"and wanting to spend more and more\\ntime together.\", \"This first stage of love is what\\npsychologists call infatuation,\", \"or passionate love.\", \"Your new relationship\\ncan feel almost intoxicating,\", \"and when it comes to the brain,\\nthat\\u2019s not far from the truth.\", \"Infatuated individuals show increased\\nactivation in the ventral tegmental area.\", \"The VTA is the reward-processing \\nand motivation hub of the brain,\", \"firing when you do things like \\neat a sweet treat, quench your thirst,\", \"or in more extreme cases,\\ntake drugs of abuse.\", \"Activation releases the \\u201cfeel good\\u201d\\nneurotransmitter dopamine,\", \"teaching your brain to repeat behaviors \\nin anticipation\", \"of receiving the same initial reward.\", \"This increased VTA activity is the\\nreason love's not only euphoric,\", \"but also draws you towards\\nyour new partner.\", \"At this first stage, it may be hard to see\\nany faults in your new perfect partner.\", \"This haze is thanks\\nto love\\u2019s influence\", \"on higher cortical brain regions.\", \"Some newly infatuated individuals\\nshow decreased activity\", \"in the brain\\u2019s cognitive center, \\nthe prefrontal cortex.\", \"As activation of this region allows us \\nto engage in critical thought\", \"and pass judgment,\", \"it\\u2019s not surprising we tend to see \\nnew relationships\", \"through rose-colored glasses.\", \"While this first stage of love can be\", \"an intense rollercoaster of emotions\\nand brain activity,\", \"it typically only lasts a few months,\", \"making way for the more long-lasting\\nstage of love,\", \"known as attachment,\\nor compassionate love.\", \"As your relationship develops,\", \"you may feel more relaxed \\nand committed to your partner\", \"thanks in large part to two hormones:\\noxytocin and vasopressin.\", \"Known as pair-bonding hormones,\", \"they signal trust, \\nfeelings of social support and attachment.\", \"In this way, romantic love \\nis not unlike other forms of love,\", \"as these hormones also help bond\\nfamilies and friendships.\", \"Further, oxytocin can inhibit \\nthe release of stress hormones,\", \"which is why spending time \\nwith a loved one can feel so relaxing.\", \"As early love's suspension\\nof judgment fades,\", \"it can be replaced by a more honest\\nunderstanding and deeper connection.\", \"Alternatively, as your rose-colored\\nglasses begin to lose their tint,\", \"problems in your relationship\\nmay become more evident.\", \"No matter the reason \\na relationship ends,\", \"we can blame the pain that accompanies\\nheartbreak on the brain.\", \"The distress of a breakup activates\\nthe insular cortex,\", \"a region that processes pain\\u2014\", \"both physical, \\nlike spraining your ankle,\", \"as well as social, \\nlike the feelings of rejection.\", \"As days pass, you may find yourself\\nonce again daydreaming about\", \"or craving contact with your lost partner.\", \"The drive to reach out may\\nfeel overwhelming,\", \"like an extreme hunger or thirst.\", \"When looking at photos\\nof a former partner,\", \"heartbroken individuals again show\\nincreased activity in the VTA,\", \"the motivation and reward center \\nthat drove feelings of longing\", \"during the initial stages \\nof the relationship.\", \"This emotional whirlwind also likely\\nactivates your body\\u2019s alarm system,\", \"the stress axis, leaving you feeling \\nshaken and restless.\", \"As time goes on,\", \"higher cortical regions which oversee \\nreasoning and impulse control,\", \"can pump the brakes on this distress\\nand craving signaling.\", \"Given that these regions\\nare still maturing\", \"and making connections\\nthrough adolescence,\", \"it's no wonder that first heartbreak\\ncan feel particularly agonizing.\", \"Activities like exercise, \\nspending time with friends,\", \"or even listening to your favorite song\", \"can tame this heartbreak stress response,\", \"while also triggering the release \\nof feel good neurotransmitter dopamine.\", \"And given time and the support,\", \"most can heal and learn from even\\nthe most devastating heartbreak.\"]"}, {"role": "assistant", "content": "Love and its effects on the brain are discussed in detail in this transcript. There are three stages of love: infatuation or passionate love, attachment, and heartbreak. During infatuation, the VTA or reward-processing and motivation hub of the brain is highly activated, triggering the release of dopamine, which reinforces behavior, teaching the brain to repeat the same initial reward. As a result, new partners feel euphoric and drawn to one another. In this phase, the brain's cognitive centre, the prefrontal cortex, is less activated, so individuals tend to see their new partners through rose-coloured glasses.\n\nThe second stage is attachment, which is characterised by two hormones, oxytocin and vasopressin, that signal trust, social support and attachment, leading to a deeper connection between partners. This stage of love is more long-lasting than infatuation, and individuals tend to be more relaxed and committed to their partner.\n\nThe final stage is heartbreak, which is characterised by the activation of the insular cortex that processes emotional pain. Heartbroken individuals crave contact and show increased activity in the VTA when looking at photos of their lost partners. The stress axis is activated, leaving individuals feeling shaken and restless, but activities like exercise or spending time with friends can help alleviate this stress response and trigger the release of feel-good neurotransmitter dopamine.\n\nIn conclusion, love is a complex and multi-staged phenomenon that impacts a range of neural circuits in the brain, leading to an array of emotions that can be both uplifting and painful. Understanding the brain's role in love can help us better comprehend and cope with the ups and downs of romantic relationships."}]}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def home():
    return "Works!"

@app.route('/mp4', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        filename = secure_filename(file.filename)
        mp4_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(mp4_path)

        mp3_path = os.path.splitext(mp4_path)[0] + '.mp3'
        convert_mp4_to_mp3(mp4_path, mp3_path)

        text = transcribe_audio_with_whisper(mp3_path)
        gpt_prompt = "Summarize the content of this transcript in 250 words indetail giving information on each of the subtopics in the transcript: " + text

        #   resp = openai.ChatCompletion.create(model="gpt-3.5-turbo",
        #                                       messages=[{"role": "user", "content": gpt_prompt}])

        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": gpt_prompt},
            ]
        )

        response_content = resp.choices[0].message.content


        fullresponse = {
            "messages": [
                {"role": 'user', "content": gpt_prompt},
                {"role": 'assistant', "content": response_content}],
        }

        print(fullresponse)

        return (json.dumps(fullresponse))
    finally:
        if mp4_path and os.path.exists(mp4_path):
            os.remove(mp4_path)
        if mp3_path and os.path.exists(mp3_path):
            os.remove(mp3_path)

@app.route('/youtube',  methods=['POST'])
def getTranscript():
    try:
        youtubeURL = request.get_json()["youtubeURL"]
        youtubeURL = youtubeURL.replace("https://www.youtube.com/watch?v=", "")
        transcript = YouTubeTranscriptApi.get_transcript(youtubeURL)
        json_formatted = JSONFormatter().format_transcript(transcript)
        json_editable = json.loads(json_formatted)

        newlist = []

        for item in json_editable:
            newlist.append(item["text"])

        shortened = json.dumps(newlist)

        gpt_prompt = "Summarize the content of this transcript in 250 words indetail giving information on each of the subtopics in the transcript: " + shortened

    #   resp = openai.ChatCompletion.create(model="gpt-3.5-turbo",
    #                                       messages=[{"role": "user", "content": gpt_prompt}])

        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": gpt_prompt},
            ]
        )

        response_content = resp.choices[0].message.content


        fullresponse = {
            "messages": [
                {"role": 'user', "content": gpt_prompt},
                {"role": 'assistant', "content": response_content}],
        }


        return (json.dumps(fullresponse))

    except Exception as e:
        print(str(e))
        abort(404, description=str(e))


@app.route('/conversation',  methods=['POST'])
def getGPTReply():
    try:
        messages = request.get_json()
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        return (json.dumps(resp))

    except Exception as e:
        print(str(e))
        abort(404, description=str(e))

def convert_mp4_to_mp3(mp4_path, mp3_path):
    try:
        (
            ffmpeg
            .input(mp4_path)
            .output(mp3_path, **{'q:a': 0})
            .run(overwrite_output=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr)
        raise

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'mp4'

def transcribe_audio_with_whisper(audio_path):
    # Load the Whisper model
    model = whisper.load_model("base")

    # Process the audio file and transcribe it
    result = model.transcribe(audio_path)
    return result['text']

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run()
