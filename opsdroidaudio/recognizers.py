"""Speech to text recognizer functions."""
H='No speech found in audio.'
G=False
E=None
import logging as F
from speech_recognition import Recognizer as A,AudioData as B,UnknownValueError as C
D=F.getLogger(__name__)
def I(config,data,sample_rate):
	I=B(data,sample_rate,2)
	try:F=A().recognize_google_cloud(I,credentials_json=E,language='en-GB',preferred_phrases=E,show_all=G)
	except C:F='';D.warning(H)
	return F
def J(config,data,sample_rate):
	I=B(data,sample_rate,2)
	try:F=A().recognize_sphinx(I,language='en-US',keyword_entries=E,show_all=G)
	except C:F='';D.warning(H)
	return F
