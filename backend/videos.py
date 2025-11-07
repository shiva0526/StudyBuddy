import os
from typing import List, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from backend.embeddings import get_embedding, cosine_similarity

def search_youtube_videos(topic: str, max_results: int = 5) -> List[Dict]:
    """
    Search YouTube for educational videos on topic
    Returns list of {video_id, title, description, url}
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    if not api_key:
        return [{
            "video_id": "dQw4w9WgXcQ",
            "title": f"Learn {topic} - Tutorial",
            "description": "Educational video (YouTube API key not configured)",
            "url": f"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "mock": True
        }]
    
    try:
        import googleapiclient.discovery
        
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
        
        request = youtube.search().list(
            part="snippet",
            q=f"{topic} tutorial explain",
            type="video",
            maxResults=max_results,
            relevanceLanguage="en"
        )
        response = request.execute()
        
        videos = []
        for item in response.get("items", []):
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        
        return videos
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []

def get_video_transcript(video_id: str) -> str:
    """Get transcript for a YouTube video"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([entry['text'] for entry in transcript_list])
        return transcript
    except Exception as e:
        print(f"Transcript fetch error for {video_id}: {e}")
        return ""

def find_best_videos_for_topic(topic: str, max_videos: int = 3) -> List[Dict]:
    """
    Find and rank best videos for a topic using transcript similarity
    Returns list of {video_id, title, url, relevance_score, snippet}
    """
    videos = search_youtube_videos(topic, max_results=5)
    
    if not videos or videos[0].get("mock"):
        return videos[:max_videos]
    
    topic_embedding = get_embedding(topic)
    ranked_videos = []
    
    for video in videos:
        transcript = get_video_transcript(video["video_id"])
        
        if transcript:
            transcript_snippet = transcript[:1000]
            transcript_embedding = get_embedding(transcript_snippet)
            similarity = cosine_similarity(topic_embedding, transcript_embedding)
            
            video["relevance_score"] = round(similarity, 3)
            video["snippet"] = transcript[:300]
            ranked_videos.append(video)
        else:
            video["relevance_score"] = 0.5
            video["snippet"] = video.get("description", "")[:300]
            ranked_videos.append(video)
    
    ranked_videos.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return ranked_videos[:max_videos]
