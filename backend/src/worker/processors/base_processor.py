"""
Base processor class.
"""


class BaseProcessor:
    """Base class for job processors."""
    
    def process(self, message: dict):
        """Process a job message."""
        job_type = message.get("job_type")
        
        if job_type == "ingest_content":
            return self.handle_ingest(message)
        elif job_type == "analyze_content":
            return self.handle_analyze(message)
        elif job_type == "cluster_user":
            return self.handle_cluster(message)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    
    def handle_ingest(self, message: dict):
        """Handle content ingestion job."""
        raise NotImplementedError
    
    def handle_analyze(self, message: dict):
        """Handle content analysis job."""
        raise NotImplementedError
    
    def handle_cluster(self, message: dict):
        """Handle clustering job."""
        raise NotImplementedError
