from typing import Dict, List
from autogen import ConversableAgent
import sys
import os
import pprint
from fuzzywuzzy import fuzz
from collections import defaultdict
import ast
import re
import math

def read_txt_file(path: str) -> Dict[str, List[str]]: 
    pattern = ". "
    dict_res = defaultdict(list)
    lst_res = []
    with open(path, 'r') as file:
        for line in file:
            # Strip newline character and print the line
            lst = line.strip().split(pattern)
            restaurant = lst[0]
            review = str(pattern.join(lst[1:]))
            lst_res.append((restaurant, review))
    for name, review in lst_res:
        dict_res[name].append(review)
    return dict_res


def fetch_restaurant_data(restaurant_name: str) -> Dict[str, List[str]]:
    # This function takes in a restaurant name and returns the reviews for that restaurant. 
    # The output should be a dictionary with the key being the restaurant name and the value being a list of reviews for that restaurant.
    # The "data fetch agent" should have access to this function signature, and it should be able to suggest this as a function call. 
    # Example:
    # > fetch_restaurant_data("Applebee's")
    # {"Applebee's": ["The food at Applebee's was average, with nothing particularly standing out.", ...]}
    dic_res = read_txt_file("./restaurant-data.txt")
    for k in dic_res.keys():
        print(fuzz.ratio(restaurant_name.lower(), k.lower()), restaurant_name.lower(), k.lower())
        if fuzz.ratio(restaurant_name.lower(), k.lower()) >= 65:
            return {k: dic_res[k]}
    return {"Applebee's": ["The food at Applebee's was average, with nothing particularly standing out."]}


def get_score(review_with_score: str) -> Dict[str, int]:
    # This function takes reviews with scores on food and customer quality, extract numeric food_score and customer_service_score 
    pattern = r"food_score\s*[=:]\s*(\d+)|customer_service_score\s*[=:]\s*(\d+)"

    # Find all matches
    matches = re.findall(pattern, review_with_score.lower())

    # Extract scores
    food_score = next((int(m[0]) for m in matches if m[0]), None)
    customer_service_score = next((int(m[1]) for m in matches if m[1]), None)

    
    if food_score not in [e for e in range(1,6)]:
        food_score = int(food_score*5)
    if customer_service_score not in [e for e in range(1,6)]:
        customer_service_score = int(customer_service_score*5)
    print("Food Score:", food_score)  # Output: 2
    print("Customer Service Score:", customer_service_score)  # Output: 3
    return {'food_score': food_score, 'customer_service_score': customer_service_score}


def calculate_overall_score(restaurant_name: str, food_scores: List[int], customer_service_scores: List[int]) -> Dict[str, float]:
    # TODO
    # This function takes in a restaurant name, a list of food scores from 1-5, and a list of customer service scores from 1-5
    # The output should be a score between 0 and 10, which is computed as the following:
    # SUM(sqrt(food_scores[i]**2 * customer_service_scores[i]) * 1/(N * sqrt(125)) * 10
    # The above formula is a geometric mean of the scores, which penalizes food quality more than customer service. 
    # Example:
    # > calculate_overall_score("Applebee's", [1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    # {"Applebee's": 5.048}
    # NOTE: be sure to that the score includes AT LEAST 3  decimal places. The public tests will only read scores that have 
    # at least 3 decimal places.
    summ = 0.0
    for food_score, customer_score in zip(food_scores, customer_service_scores):
        summ += math.sqrt(float(food_score**2) * float(customer_score))
    return {restaurant_name: summ / len(food_scores) / math.sqrt(125) * 10}


# Do not modify the signature of the "main" function.
def main(user_query: str):
    entrypoint_agent_system_message = "You are a helpful assistant. Your task is to send requests to other agents, receive returns and trigger necessary functions, handle other necessary processing or manipulation steps." # TODO
    # example LLM config for the entrypoint agent
    # llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]}
    llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": ""}]}
    # the main entrypoint/supervisor agent
    entrypoint_agent = ConversableAgent("entrypoint_agent", 
                                        system_message=entrypoint_agent_system_message, 
                                        llm_config=llm_config)
    entrypoint_agent.register_for_llm(name="fetch_restaurant_data", description="Fetches the reviews for a specific restaurant.")(fetch_restaurant_data)

    # TODO
    # Create more agents here. 
    # Create an agent to extract a list of reviews
    datafetch_agent_system_message = "You are a Data Fetch Agent. Your task is to extract the name of the restaurant mentioned in the user's query."
    datafetch_agent = ConversableAgent("datafetch_agent", 
                                        system_message=datafetch_agent_system_message, 
                                        llm_config=llm_config)
    datafetch_agent.register_for_execution(name="fetch_restaurant_data")(fetch_restaurant_data)
    # Create an agent for review
    reviewanalysis_agent_system_message = """You are a Review Analysis Agent. You will be provided a review, your task is to extract comment from the review on food and customer service quality, thus scoring these two aspects. Each review has keyword adjectives that correspond to the score that the restaurant should get for its food_score and customer_service_score. Here are the keywords the agent should look out for:
Score 1/5 has one of these adjectives: awful, horrible, or disgusting.
Score 2/5 has one of these adjectives: bad, unpleasant, or offensive.
Score 3/5 has one of these adjectives: average, uninspiring, or forgettable.
Score 4/5 has one of these adjectives: good, enjoyable, or satisfying.
Score 5/5 has one of these adjectives: awesome, incredible, or amazing.
Note that the review might not exactly use these words to describe food or customer service quality. If that is the case, please use these as refereces to score based on most similar words.
Please provide food_score and customer_service_score separately."""
    reviewanalysis_agent = ConversableAgent("reviewanalysis_agent", 
                                        system_message=reviewanalysis_agent_system_message, 
                                        llm_config=llm_config)
    # Extract reviews
    chat_result = entrypoint_agent.initiate_chat(datafetch_agent, 
                                                 message=f"What is the name of the restaurant mentioned in the following query: \'{user_query}\'?", 
                                                 max_turns=2,
                                                 summary_method='last_msg')

    # List all review
    review_dict = ast.literal_eval(chat_result.summary)
    lst_review = []
    for k, v in review_dict.items():
        restaurant_name = k
        for review in v:
            lst_review.append(review)

   
    
    # List all food score and customer service score
    food_scores = []
    service_scores = []
    for e in lst_review:
        chat_result = entrypoint_agent.initiate_chat(reviewanalysis_agent, 
                                                message=f"Based on this review \'{e}\', what are food_score and customer_service_score? ", 
                                                max_turns=1,
                                                summary_method='last_msg')
        review_with_score = chat_result.summary
        scores = get_score(review_with_score=review_with_score)
        food_score, service_score = scores['food_score'], scores['customer_service_score']
        food_scores.append(food_score)
        service_scores.append(service_score)
    # calculate score
    print(calculate_overall_score(restaurant_name=restaurant_name, food_scores=food_scores, customer_service_scores=service_scores))
    
# DO NOT modify this code below.
if __name__ == "__main__":
    assert len(sys.argv) > 1, "Please ensure you include a query for some restaurant when executing main."
    main(sys.argv[1])