# import os
# import sys
# from datetime import datetime, timedelta
# import random
# from typing import Dict, List

# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from grants_db import insert_grant
# from utils import generate_link_hash

# FAKE_GRANTS_DATA: List[Dict] = [
#     {
#         "title": "Community Health & Education Fund",
#         "description_short": "Funding for grassroots initiatives improving health literacy and access to basic education in underserved communities.",
#         "description_long": "This grant aims to support non-profit organizations working at the community level to enhance health awareness, provide preventative care education, and establish literacy programs for adults and children in rural and urban poor areas. Priority will be given to projects that demonstrate sustainable impact and community participation.",
#         "link": "https://fakegrant.org/health-edu-fund-1",
#         "application_deadline": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Health", "Education", "Community Development"],
#         "target_beneficiaries": ["Underserved communities", "Children", "Adult learners"],
#         "geographic_eligibility": ["Global"],
#         "min_budget": 20000,
#         "max_budget": 100000,
#         "keywords": ["health", "education", "community", "literacy", "wellness"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_3_good_health_and_well_being", "sdg_goal_4_quality_education"],
#         "is_active": True
#     },
#     {
#         "title": "Women's Economic Empowerment in Africa",
#         "description_short": "Grants for projects empowering women through skill development, entrepreneurship, and access to finance in Sub-Saharan Africa.",
#         "description_long": "Supports initiatives focused on vocational training for women, micro-enterprise development, financial literacy programs, and establishing women-led cooperatives to foster economic independence across various African nations.",
#         "link": "https://fakegrant.org/women-africa-2",
#         "application_deadline": (datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Women Empowerment", "Economic Development", "Entrepreneurship"],
#         "target_beneficiaries": ["Women", "Girls", "Female entrepreneurs"],
#         "geographic_eligibility": ["Sub-Saharan Africa"],
#         "min_budget": 50000,
#         "max_budget": 250000,
#         "keywords": ["women", "empowerment", "africa", "economic", "entrepreneurship", "gender"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_5_gender_equality", "sdg_goal_8_decent_work_and_economic_growth"],
#         "is_active": True
#     },
#     {
#         "title": "Sustainable Urban Green Spaces Grant",
#         "description_short": "Funding for initiatives creating and maintaining green spaces, urban gardens, and promoting biodiversity in cities.",
#         "description_long": "This grant supports NGOs and community groups dedicated to enhancing urban biodiversity, developing public parks, managing community gardens, and fostering sustainable urban planning practices. Focus on climate resilience and community engagement.",
#         "link": "https://fakegrant.org/urban-green-3",
#         "application_deadline": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Environmental Conservation", "Urban Development", "Biodiversity", "Climate Action"],
#         "target_beneficiaries": ["Urban communities", "City residents", "Local authorities"],
#         "geographic_eligibility": ["Global (Urban Centers)"],
#         "min_budget": 20000,
#         "max_budget": 75000,
#         "keywords": ["urban", "green", "environment", "biodiversity", "sustainability", "climate"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_11_sustainable_cities_and_communities", "sdg_goal_13_climate_action", "sdg_goal_15_life_on_land"],
#         "is_active": True
#     },
#     {
#         "title": "Clean Water Access for Rural Areas",
#         "description_short": "Supports projects providing clean drinking water solutions and sanitation facilities in remote rural areas.",
#         "description_long": "This grant focuses on sustainable water management, drilling boreholes, installing water purification systems, and educating communities on hygiene practices in rural settings where access to clean water is limited.",
#         "link": "https://fakegrant.org/water-rural-4",
#         "application_deadline": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Water", "Sanitation", "Community Health"],
#         "target_beneficiaries": ["Rural communities", "Vulnerable populations"],
#         "geographic_eligibility": ["Specific Developing Countries"],
#         "min_budget": 30000,
#         "max_budget": 150000,
#         "keywords": ["water", "sanitation", "rural", "clean", "hygiene"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_6_clean_water_and_sanitation"],
#         "is_active": True
#     },
#     {
#         "title": "Peacebuilding and Justice Initiatives",
#         "description_short": "Grants for NGOs working on conflict resolution, access to justice, and strengthening democratic institutions.",
#         "description_long": "Funds projects promoting peaceful and inclusive societies, supporting legal aid services, fostering good governance, and building capacity for local institutions to ensure justice for all. Focus on post-conflict regions.",
#         "link": "https://fakegrant.org/peace-justice-5",
#         "application_deadline": (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Peacebuilding", "Justice", "Governance", "Human Rights"],
#         "target_beneficiaries": ["Conflict-affected communities", "Legal professionals", "Local government"],
#         "geographic_eligibility": ["Global (Conflict Regions)"],
#         "min_budget": 75000,
#         "max_budget": 300000,
#         "keywords": ["peace", "justice", "conflict", "governance", "human rights"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_16_peace_justice_and_strong_institutions"],
#         "is_active": True
#     },
#      {
#         "title": "Youth STEM Education Program",
#         "description_short": "Supporting initiatives focused on promoting Science, Technology, Engineering, and Mathematics (STEM) education among youth.",
#         "description_long": "This grant aims to foster innovation and future leadership by providing resources for STEM education, coding bootcamps, and robotics workshops for young people in underserved areas. Focus on practical skills and career readiness.",
#         "link": "https://fakegrant.org/youth-stem-6",
#         "application_deadline": (datetime.now() + timedelta(days=75)).strftime("%Y-%m-%d"),
#         "focus_areas": ["Education", "Youth Development", "Technology", "Innovation"],
#         "target_beneficiaries": ["Youth (10-24 years)", "Students", "Aspiring innovators"],
#         "geographic_eligibility": ["Local", "National"],
#         "min_budget": 15000,
#         "max_budget": 90000,
#         "keywords": ["youth", "stem", "education", "technology", "innovation", "skills"],
#         "source": "FakeGrantsOrg",
#         "sdg_tags": ["sdg_goal_4_quality_education", "sdg_goal_9_industry_innovation_and_infrastructure"],
#         "is_active": True
#     }
# ]

# def populate_database_with_fake_grants():
#     """
#     Populates the grants table with predefined fake data.
#     Generates link_hash and handles date formatting.
#     """
#     print("Starting database population with fake grants...")
#     inserted_count: int = 0
#     for grant_data in F