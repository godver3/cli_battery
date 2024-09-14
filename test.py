import requests
import time
import random
import concurrent.futures

# Sample IMDb IDs (replace these with actual IDs)
MOVIE_IDS = ["tt0111161", "tt0068646", "tt0071562", "tt0468569", "tt0050083",
             "tt0108052", "tt0167260", "tt0110912", "tt0060196", "tt0120737",
             "tt0109830", "tt0137523", "tt0080684", "tt1375666", "tt0167261",
             "tt0073486", "tt0099685", "tt0133093", "tt0047478", "tt0114369"]

TV_SHOW_IDS = ["tt0944947", "tt0903747", "tt0475784", "tt1475582", "tt0185906",
               "tt0306414", "tt0417299", "tt2395695", "tt0081846", "tt0141842",
               "tt2861424", "tt0098904", "tt0386676", "tt0213338", "tt2442560",
               "tt0773262", "tt0412142", "tt0121955", "tt0795176", "tt0096697"]

BASE_URL = "http://localhost:5001/api"

def fetch_metadata(imdb_id):
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/metadata/{imdb_id}")
    end_time = time.time()
    return end_time - start_time

def fetch_seasons(imdb_id):
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/seasons/{imdb_id}")
    end_time = time.time()
    return end_time - start_time

def run_test(test_type, ids, fetch_function):
    total_time = 0
    for imdb_id in ids:
        time_taken = fetch_function(imdb_id)
        total_time += time_taken
        print(f"{test_type} - IMDB ID: {imdb_id}, Time: {time_taken:.4f} seconds")
    avg_time = total_time / len(ids)
    print(f"\nAverage time for {test_type}: {avg_time:.4f} seconds")
    return avg_time

def main():
    print("Starting Metadata Battery Speed Test")
    
    movie_avg = run_test("Movies", MOVIE_IDS, fetch_metadata)
    tv_show_avg = run_test("TV Shows", TV_SHOW_IDS, fetch_metadata)
    seasons_avg = run_test("Seasons", TV_SHOW_IDS, fetch_seasons)
    
    print("\nOverall Results:")
    print(f"Movies Metadata Average: {movie_avg:.4f} seconds")
    print(f"TV Shows Metadata Average: {tv_show_avg:.4f} seconds")
    print(f"Seasons Data Average: {seasons_avg:.4f} seconds")

if __name__ == "__main__":
    main()
