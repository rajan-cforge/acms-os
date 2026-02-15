#!/usr/bin/env python3
"""
ACMS User Generator - Create 5,000 users for Bay Area tech company

Usage:
    python scripts/create_users.py --count 5000
"""

import asyncio
import random
import argparse
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import get_session
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Bay Area tech company departments
DEPARTMENTS = [
    "Engineering", "Product", "Design", "Data Science", "DevOps",
    "Security", "QA", "Mobile", "Infrastructure", "ML/AI",
    "Sales", "Marketing", "Customer Success", "Support",
    "Finance", "HR", "Legal", "Operations", "Facilities",
    "Executive"
]

# First names (mix of common names)
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Wei", "Priya", "Raj", "Yuki", "Carlos", "Ananya", "Luis", "Mei", "Ahmed", "Sofia",
    "Ali", "Maria", "Chen", "Elena", "Hassan", "Nina", "Park", "Ava", "Kim", "Grace"
]

# Last names (mix of common names)
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris",
    "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen",
    "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter",
    "Wang", "Patel", "Kumar", "Sharma", "Gupta", "Chen", "Kim", "Li", "Singh", "Khan",
    "Park", "Yamamoto", "Suzuki", "Tanaka", "Silva", "Santos", "Costa", "Oliveira"
]

# Tech company email domains
EMAIL_DOMAIN = "acmetech.com"


def generate_user_data(index: int) -> Dict:
    """Generate realistic user data for a tech company employee."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    # Create username with some variation (unique identifier)
    username_formats = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}{last_name[0].lower()}",
    ]

    username = random.choice(username_formats).replace(" ", "")
    if index > 100:  # Add numbers for later users to ensure uniqueness
        username = f"{username}{index}"

    # Create email with some variation
    email_formats = [
        f"{first_name.lower()}.{last_name.lower()}@{EMAIL_DOMAIN}",
        f"{first_name[0].lower()}{last_name.lower()}@{EMAIL_DOMAIN}",
        f"{first_name.lower()}{last_name[0].lower()}@{EMAIL_DOMAIN}",
    ]

    # Add number suffix to ensure uniqueness
    email = random.choice(email_formats).replace(" ", "")
    if index > 100:  # Add numbers for later users to ensure uniqueness
        email = email.replace(f"@{EMAIL_DOMAIN}", f"{index}@{EMAIL_DOMAIN}")

    # Generate created date (employees joined over the last 5 years)
    days_ago = random.randint(0, 1825)  # 5 years
    created_at = datetime.utcnow() - timedelta(days=days_ago)

    return {
        "user_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "display_name": f"{first_name} {last_name}",
        "is_active": random.random() > 0.02,  # 98% active users
        "created_at": created_at
    }


async def create_users_batch(users: List[Dict]):
    """Insert a batch of users into the database."""
    try:
        async with get_session() as db:
            # Use raw SQL for bulk insert
            for user in users:
                query = text("""
                    INSERT INTO users (user_id, username, email, display_name, is_active, created_at)
                    VALUES (:user_id, :username, :email, :display_name, :is_active, :created_at)
                    ON CONFLICT (username) DO NOTHING
                """)
                await db.execute(query, user)

            await db.commit()
            return len(users)
    except Exception as e:
        logger.error(f"Error inserting batch: {e}")
        return 0


async def generate_users_async(total_count: int, batch_size: int):
    """Generate users asynchronously with batching."""
    total_batches = (total_count + batch_size - 1) // batch_size
    successful = 0
    failed = 0

    logger.info(f"Starting user generation: {total_count} total, {batch_size} per batch")
    logger.info(f"Total batches: {total_batches}")

    start_time = datetime.now()

    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, total_count)
        batch_count = batch_end - batch_start

        # Generate batch
        logger.info(f"Generating batch {batch_num + 1}/{total_batches} ({batch_count} users)...")
        users = [generate_user_data(i) for i in range(batch_start, batch_end)]

        # Insert batch
        inserted = await create_users_batch(users)
        successful += inserted
        failed += (batch_count - inserted)

        # Progress
        progress = ((batch_num + 1) / total_batches) * 100
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = successful / elapsed if elapsed > 0 else 0

        logger.info(
            f"Batch {batch_num + 1}/{total_batches} ({progress:.1f}%) | "
            f"Success: {successful} | Failed: {failed} | Rate: {rate:.1f}/s"
        )

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info("User Generation Complete!")
    logger.info("=" * 60)
    logger.info(f"Total created: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Time taken: {elapsed / 60:.1f} minutes")
    logger.info(f"Average rate: {successful / elapsed:.1f} users/second")
    logger.info("=" * 60)

    return successful


def main():
    parser = argparse.ArgumentParser(description="Generate users for ACMS")
    parser.add_argument("--count", type=int, default=5000, help="Total number of users to generate")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of users per batch")

    args = parser.parse_args()

    logger.info("Configuration:")
    logger.info(f"  Total users: {args.count}")
    logger.info(f"  Batch size: {args.batch_size}")

    # Run async generation
    asyncio.run(generate_users_async(args.count, args.batch_size))


if __name__ == "__main__":
    main()
