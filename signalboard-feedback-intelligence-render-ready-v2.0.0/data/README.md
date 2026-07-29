# Real-data sample

`cfpb_feedback_sample.csv` contains 250 public consumer complaint narratives transformed from the U.S. Consumer Financial Protection Bureau Consumer Complaint Database.

Mapping used:

- complaint narrative → `feedback_text`
- submitted channel → `source`
- public tags → `user_type`
- product and issue → `product_area`
- date received → `date`
- complaint ID → `external_id`

The database publishes narratives with consumer consent after taking steps to remove personal information. Narratives represent consumer-submitted accounts and are not independently verified. This sample is used only to test ingestion, clustering, evidence grounding, analytics, and review workflows on realistic long-form text.

Source documentation: CFPB Consumer Complaint Database and API documentation.
