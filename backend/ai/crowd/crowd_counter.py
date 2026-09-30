import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.events import CrowdMetric

logger = logging.getLogger("crowd_safety.ai.crowd_counter")

class CrowdCounter:
    """
    Manages crowd calculation state (Current, Peak, Average)
    and periodically persists crowd metrics to the database.
    """
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self.last_db_persist_time: float = 0.0
        self.persist_interval_sec: float = 10.0  # Log metric every 10 seconds to avoid DB bloat

    def record_metrics(self, db: Optional[Session], current_people: int, average_movement_speed: float = 0.0):
        now = time.time()
        if db is None:
            return

        # Check if 10 seconds have elapsed since last write
        if now - self.last_db_persist_time >= self.persist_interval_sec:
            try:
                # Classify density based on people count
                if current_people >= 40:
                    density = "CRITICAL"
                elif current_people >= 25:
                    density = "HIGH"
                elif current_people >= 10:
                    density = "MEDIUM"
                else:
                    density = "LOW"

                metric = CrowdMetric(
                    camera_id=self.camera_id,
                    people_count=current_people,
                    density_level=density,
                    movement_speed=round(average_movement_speed, 2)
                )
                db.add(metric)
                db.commit()
                self.last_db_persist_time = now
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting crowd metric for camera {self.camera_id}: {e}")
