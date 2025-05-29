from common.database.cosmos.db_operations import fetch_top_k_candidates_by_count, fetch_top_k_candidates_by_percentage, update_application_status

x = 123486

print(fetch_top_k_candidates_by_count(x))