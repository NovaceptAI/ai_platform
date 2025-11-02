import os
import docx
try:
	import PyPDF2
except Exception:
	PyPDF2 = None
try:
	from pydub import AudioSegment
except Exception:
	AudioSegment = None
try:
	import moviepy.editor as mp
except Exception:
	mp = None
try:
	import boto3
	from botocore.exceptions import ClientError, NoCredentialsError
except Exception:
	boto3 = None
try:
	from pptx import Presentation
except Exception:
	Presentation = None
try:
	import openpyxl
except Exception:
	openpyxl = None
try:
	from PIL import Image
except Exception:
	Image = None
from app.services.lemonfox_service import transcribe_audio_with_timestamps
from app.services.whisper_service import translate_audio_with_azure_whisper
from transformers import GPT2TokenizerFast
# transcriber = AzureWhisperTranscriber()

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
TOKEN_LIMIT = 1500  # You can tweak this
AUDIO_TIME_LIMIT = 60  # seconds per page for audio/video
AUDIO_WORD_LIMIT = 200  # words per page for audio/video

def chunk_audio_segments_by_limits(segments, time_limit=AUDIO_TIME_LIMIT, word_limit=AUDIO_WORD_LIMIT):
	"""
	Chunks audio segments into pages based on time or word limits.
	Returns: list of chunks, where each chunk contains multiple segments
	"""
	chunks = []
	current_chunk = {
		'segments': [],
		'text': '',
		'start_time': None,
		'end_time': None,
		'start_seconds': None,
		'end_seconds': None,
		'word_count': 0,
		'duration': 0
	}
	
	for segment in segments:
		segment_words = len(segment['text'].split())
		segment_duration = segment['duration']
		
		# Check if adding this segment would exceed limits
		would_exceed_words = current_chunk['word_count'] + segment_words > word_limit
		would_exceed_time = current_chunk['duration'] + segment_duration > time_limit
		
		# If chunk is not empty and would exceed limits, save current chunk and start new one
		if current_chunk['segments'] and (would_exceed_words or would_exceed_time):
			chunks.append(current_chunk)
			current_chunk = {
				'segments': [],
				'text': '',
				'start_time': None,
				'end_time': None,
				'start_seconds': None,
				'end_seconds': None,
				'word_count': 0,
				'duration': 0
			}
		
		# Add segment to current chunk
		current_chunk['segments'].append(segment)
		current_chunk['text'] += segment['text'] + ' '
		current_chunk['word_count'] += segment_words
		current_chunk['duration'] += segment_duration
		
		# Set start time (first segment in chunk)
		if current_chunk['start_time'] is None:
			current_chunk['start_time'] = segment['start']
			current_chunk['start_seconds'] = segment['start_seconds']
		
		# Always update end time (last segment so far)
		current_chunk['end_time'] = segment['end']
		current_chunk['end_seconds'] = segment['end_seconds']
	
	# Add the last chunk if it has content
	if current_chunk['segments']:
		chunks.append(current_chunk)
	
	return chunks

def detect_file_type(file_path):
	"""Detects the file type based on its extension."""
	if file_path.endswith(('.docx', '.pdf', '.txt')):
		return "document"
	elif file_path.endswith(('.mp3', '.wav', '.m4a')):
		return "audio"
	elif file_path.endswith(('.mp4', '.avi', '.mov')):
		return "video"
	elif file_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')):
		return "image"
	elif file_path.endswith('.pptx'):
		return "presentation"
	elif file_path.endswith(('.xlsx', '.xls')):
		return "spreadsheet"
	else:
		raise ValueError("Unsupported file format")

def extract_text_from_document(file_path):
	"""Returns a list of chunks: pages for PDFs, token-wise for DOCX/TXT."""
	if file_path.endswith('.pdf'):
		if PyPDF2 is None:
			raise RuntimeError("PyPDF2 not available")
		with open(file_path, 'rb') as file:
			reader = PyPDF2.PdfReader(file)
			return [page.extract_text() or "" for page in reader.pages]

	elif file_path.endswith('.docx'):
		doc = docx.Document(file_path)
		text = '\n'.join([para.text for para in doc.paragraphs])
		return _chunk_by_token(text)

	elif file_path.endswith('.txt'):
		with open(file_path, 'r', encoding='utf-8') as f:
			text = f.read()
		return _chunk_by_token(text)

	else:
		raise ValueError("Unsupported document format")


def _chunk_by_token(text, token_limit=TOKEN_LIMIT):
	"""Splits text into token-sized chunks."""
	words = text.split()
	chunks, current_chunk = [], []

	for word in words:
		current_chunk.append(word)
		if len(tokenizer.encode(' '.join(current_chunk))) > token_limit:
			chunks.append(' '.join(current_chunk[:-1]))
			current_chunk = [word]
	
	if current_chunk:
		chunks.append(' '.join(current_chunk))
	
	return chunks


def extract_text_from_audio(file_path):
	"""Extracts and transcribes audio to text with timestamps."""
	try:
		# Check file size and use optimized processing for large files
		file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
		
		if file_size_mb > 200:  # Use optimized processing for files > 200MB
			from app.utils.optimized_file_utils import extract_text_from_audio_optimized
			return extract_text_from_audio_optimized(file_path)
		else:
			return transcribe_audio_with_timestamps(file_path)
	finally:
		if os.path.exists(file_path):
			os.remove(file_path)

def extract_text_from_video(file_path):
	"""Extracts audio from video and transcribes it to text with timestamps."""
	if mp is None:
		raise RuntimeError("moviepy not available")
	
	# Check file size and use optimized processing for large files
	file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
	
	if file_size_mb > 200:  # Use optimized processing for files > 200MB
		from app.utils.optimized_file_utils import extract_text_from_video_optimized
		return extract_text_from_video_optimized(file_path)
	else:
		# Original simple processing for smaller files
		temp_audio_path = "temp_audio.wav"
		video = mp.VideoFileClip(file_path)
		video.audio.write_audiofile(temp_audio_path, verbose=False)
		try:
			return transcribe_audio_with_timestamps(temp_audio_path)
		finally:
			if os.path.exists(temp_audio_path):
				os.remove(temp_audio_path)
			video.close()  # Important: release memory


def extract_text_from_image(file_path):
	"""Extracts text from image using Amazon Textract OCR."""
	if boto3 is None:
		raise RuntimeError("boto3 not available for AWS Textract")
	
	try:
		# Initialize AWS Textract client
		textract_client = boto3.client(
			'textract',
			aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
			aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
			region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
		)
		
		# Read image file
		with open(file_path, 'rb') as image_file:
			image_bytes = image_file.read()
		
		# Call Textract detect_document_text API
		response = textract_client.detect_document_text(
			Document={'Bytes': image_bytes}
		)
		
		# Extract text from response
		text_chunks = []
		current_text = ""
		
		for block in response.get('Blocks', []):
			if block['BlockType'] == 'LINE':
				line_text = block.get('Text', '')
				current_text += line_text + '\n'
				
				# Create chunks based on token limit
				if len(tokenizer.encode(current_text)) > TOKEN_LIMIT:
					if current_text.strip():
						text_chunks.append(current_text.strip())
					current_text = ""
		
		# Add remaining text
		if current_text.strip():
			text_chunks.append(current_text.strip())
		
		# If no chunks created, return the full text as one chunk
		if not text_chunks:
			full_text = '\n'.join([block.get('Text', '') for block in response.get('Blocks', []) if block['BlockType'] == 'LINE'])
			text_chunks = [full_text] if full_text.strip() else ["No text detected in image"]
		
		return text_chunks
		
	except (ClientError, NoCredentialsError) as e:
		raise RuntimeError(f"AWS Textract error: {str(e)}")
	finally:
		if os.path.exists(file_path):
			os.remove(file_path)


def analyze_image_content(file_path):
	"""Analyzes image content using AWS Rekognition when no text is detected."""
	if boto3 is None:
		return "No text detected in this image. Please upload an image containing text for document processing."
	
	try:
		# Initialize AWS Rekognition client
		rekognition_client = boto3.client(
			'rekognition',
			aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
			aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
			region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
		)
		
		# Read image file
		with open(file_path, 'rb') as image_file:
			image_bytes = image_file.read()
		
		# Analyze image labels (objects, scenes, activities)
		labels_response = rekognition_client.detect_labels(
			Image={'Bytes': image_bytes},
			MaxLabels=10,
			MinConfidence=70
		)
		
		# Extract meaningful labels
		labels = []
		for label in labels_response.get('Labels', []):
			labels.append(label['Name'].lower())
		
		# Create descriptive message based on detected labels
		if labels:
			# Common combinations for better descriptions
			people_terms = ['person', 'people', 'human', 'man', 'woman', 'child', 'adult']
			animal_terms = ['dog', 'cat', 'pet', 'animal', 'puppy', 'kitten']
			nature_terms = ['plant', 'flower', 'tree', 'garden', 'nature', 'outdoor']
			indoor_terms = ['furniture', 'room', 'home', 'indoor', 'house']
			
			description_parts = []
			
			# Check for people
			if any(term in labels for term in people_terms):
				description_parts.append("a person")
			
			# Check for animals
			if any(term in labels for term in animal_terms):
				animal_labels = [label for label in labels if label in animal_terms]
				if 'dog' in animal_labels or any('dog' in label for label in labels):
					description_parts.append("dogs")
				elif animal_labels:
					description_parts.append("animals")
			
			# Check for activities or interactions
			if 'person' in labels and any(term in labels for term in animal_terms):
				activity = "interacting with"
			elif any(term in labels for term in ['sitting', 'standing', 'holding']):
				activity = "with"
			else:
				activity = "and"
			
			# Build description
			if len(description_parts) >= 2:
				description = f"This image contains no text. It depicts {description_parts[0]} {activity} {description_parts[1]}."
			elif description_parts:
				main_subjects = ", ".join(labels[:3])
				description = f"This image contains no text. It appears to show {main_subjects}."
			else:
				description = f"This image contains no text. It shows {', '.join(labels[:3])}."
			
			return f"{description} Please upload an image containing text for document processing and analysis."
		else:
			return "This image contains no text and the content could not be analyzed. Please upload an image containing text for document processing."
			
	except Exception as e:
		return f"This image contains no text. Image analysis failed: {str(e)}. Please upload an image containing text for document processing."


def extract_text_from_presentation(file_path):
	"""Extracts text from PowerPoint presentation."""
	if Presentation is None:
		raise RuntimeError("python-pptx not available")
	
	try:
		presentation = Presentation(file_path)
		slide_texts = []
		
		for i, slide in enumerate(presentation.slides):
			slide_text = f"--- Slide {i + 1} ---\n"
			
			for shape in slide.shapes:
				if hasattr(shape, "text") and shape.text.strip():
					slide_text += shape.text + '\n'
			
			slide_texts.append(slide_text.strip() if slide_text.strip() != f"--- Slide {i + 1} ---" else f"--- Slide {i + 1} --- (No text content)")
		
		# If slides are too small, chunk them by token limit
		if len(slide_texts) > 0:
			# Check if we need to merge small slides or split large ones
			final_chunks = []
			current_chunk = ""
			
			for slide_text in slide_texts:
				test_chunk = current_chunk + "\n\n" + slide_text if current_chunk else slide_text
				
				if len(tokenizer.encode(test_chunk)) <= TOKEN_LIMIT:
					current_chunk = test_chunk
				else:
					if current_chunk:
						final_chunks.append(current_chunk)
					# If single slide is too large, split it
					if len(tokenizer.encode(slide_text)) > TOKEN_LIMIT:
						final_chunks.extend(_chunk_by_token(slide_text))
					else:
						current_chunk = slide_text
			
			if current_chunk:
				final_chunks.append(current_chunk)
			
			return final_chunks if final_chunks else ["No text content found in presentation"]
		
		return ["No text content found in presentation"]
		
	finally:
		if os.path.exists(file_path):
			os.remove(file_path)


def extract_text_from_spreadsheet(file_path):
	"""Extracts text from Excel spreadsheet."""
	if openpyxl is None:
		raise RuntimeError("openpyxl not available")
	
	try:
		workbook = openpyxl.load_workbook(file_path, data_only=True)
		sheet_texts = []
		
		for sheet_name in workbook.sheetnames:
			sheet = workbook[sheet_name]
			sheet_text = f"--- Sheet: {sheet_name} ---\n"
			
			# Get sheet data
			sheet_data = []
			for row in sheet.iter_rows(values_only=True):
				row_data = []
				for cell in row:
					if cell is not None:
						row_data.append(str(cell))
					else:
						row_data.append("")
				if any(cell.strip() for cell in row_data):  # Only add non-empty rows
					sheet_data.append(row_data)
			
			# Convert to text format
			if sheet_data:
				# Add headers if first row looks like headers
				if len(sheet_data) > 1:
					headers = sheet_data[0]
					if all(isinstance(cell, str) and cell.strip() for cell in headers[:3]):  # First 3 cells are text
						sheet_text += "Headers: " + " | ".join(headers) + "\n\n"
						data_rows = sheet_data[1:]
					else:
						data_rows = sheet_data
				else:
					data_rows = sheet_data
				
				# Add data rows
				for i, row in enumerate(data_rows[:100]):  # Limit to first 100 rows
					row_text = " | ".join(str(cell) for cell in row if str(cell).strip())
					if row_text.strip():
						sheet_text += f"Row {i+1}: {row_text}\n"
			else:
				sheet_text += "No data found in this sheet\n"
			
			sheet_texts.append(sheet_text)
		
		# Chunk the combined text by token limit
		combined_text = "\n\n".join(sheet_texts)
		if combined_text.strip():
			return _chunk_by_token(combined_text)
		else:
			return ["No data found in spreadsheet"]
			
	finally:
		if os.path.exists(file_path):
			os.remove(file_path)


def extract_text_by_pages(file_path):
	"""Extracts page-wise text (PDF), or chunked token-based segments (DOCX/TXT), or appropriate chunks for other file types."""
	if file_path.endswith('.pdf'):
		if PyPDF2 is None:
			raise RuntimeError("PyPDF2 not available")
		with open(file_path, 'rb') as file:
			reader = PyPDF2.PdfReader(file)
			return [page.extract_text() or "" for page in reader.pages]

	elif file_path.endswith('.docx'):
		doc = docx.Document(file_path)
		# Chunk every N paragraphs as a 'page'
		paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
		chunk_size = 5
		return ['\n'.join(paragraphs[i:i+chunk_size]) for i in range(0, len(paragraphs), chunk_size)]

	elif file_path.endswith('.txt'):
		with open(file_path, 'r', encoding='utf-8') as f:
			text = f.read()
		tokens = text.split()
		chunk_size = 300
		return [' '.join(tokens[i:i+chunk_size]) for i in range(0, len(tokens), chunk_size)]

	elif file_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')):
		# For images, return the OCR text as single page
		return extract_text_from_image(file_path)

	elif file_path.endswith('.pptx'):
		# For presentations, each slide or group of slides becomes a page
		return extract_text_from_presentation(file_path)

	elif file_path.endswith(('.xlsx', '.xls')):
		# For spreadsheets, return chunked data
		return extract_text_from_spreadsheet(file_path)

	else:
		raise ValueError("Unsupported document format")