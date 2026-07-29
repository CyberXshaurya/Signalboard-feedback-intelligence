-- PostgreSQL 16 initial schema generated from SQLAlchemy metadata.

BEGIN;


CREATE TABLE projects (
	id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(128) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_projects_owner_id ON projects (owner_id);


CREATE TABLE datasets (
	id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_sha256 VARCHAR(64) NOT NULL, 
	total_rows INTEGER NOT NULL, 
	valid_rows INTEGER NOT NULL, 
	invalid_rows INTEGER NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	validation_errors JSON NOT NULL, 
	column_mapping JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_project_file_hash UNIQUE (project_id, file_sha256), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_datasets_project_id ON datasets (project_id);

CREATE INDEX ix_datasets_file_sha256 ON datasets (file_sha256);


CREATE TABLE historical_themes (
	id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	product_area VARCHAR(160), 
	notes TEXT, 
	active_from DATE, 
	active_until DATE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_historical_themes_project_id ON historical_themes (project_id);


CREATE TABLE analysis_runs (
	id VARCHAR(36) NOT NULL, 
	dataset_id VARCHAR(36) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	provider VARCHAR(40) NOT NULL, 
	model VARCHAR(120), 
	prompt_version VARCHAR(40) NOT NULL, 
	progress_percent INTEGER NOT NULL, 
	current_step VARCHAR(80) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	failure_code VARCHAR(100), 
	failure_message TEXT, 
	diagnostics JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
);

CREATE INDEX ix_analysis_runs_dataset_id ON analysis_runs (dataset_id);

CREATE INDEX ix_analysis_runs_status ON analysis_runs (status);


CREATE TABLE feedback_items (
	id VARCHAR(36) NOT NULL, 
	dataset_id VARCHAR(36) NOT NULL, 
	source_row INTEGER NOT NULL, 
	external_id VARCHAR(255), 
	feedback_text_original TEXT NOT NULL, 
	feedback_text_normalized TEXT NOT NULL, 
	feedback_text_masked TEXT NOT NULL, 
	source VARCHAR(120) NOT NULL, 
	user_type VARCHAR(120) NOT NULL, 
	product_area VARCHAR(160) NOT NULL, 
	feedback_date DATE NOT NULL, 
	rating FLOAT, 
	content_hash VARCHAR(64) NOT NULL, 
	duplicate_group_id VARCHAR(64), 
	validation_status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
);

CREATE INDEX ix_feedback_items_user_type ON feedback_items (user_type);

CREATE INDEX ix_feedback_items_content_hash ON feedback_items (content_hash);

CREATE INDEX ix_feedback_items_duplicate_group_id ON feedback_items (duplicate_group_id);

CREATE INDEX ix_feedback_items_feedback_date ON feedback_items (feedback_date);

CREATE INDEX ix_feedback_items_source ON feedback_items (source);

CREATE INDEX ix_feedback_items_product_area ON feedback_items (product_area);

CREATE INDEX ix_feedback_items_dataset_id ON feedback_items (dataset_id);


CREATE TABLE reports (
	id VARCHAR(36) NOT NULL, 
	project_id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	title VARCHAR(240) NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_by VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	methodology JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_reports_analysis_run_id ON reports (analysis_run_id);

CREATE INDEX ix_reports_project_id ON reports (project_id);


CREATE TABLE themes (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	title VARCHAR(240) NOT NULL, 
	summary TEXT NOT NULL, 
	problem_statement TEXT NOT NULL, 
	pattern_type VARCHAR(30) NOT NULL, 
	confidence FLOAT NOT NULL, 
	uncertainty_reason TEXT, 
	status VARCHAR(30) NOT NULL, 
	historical_relationship VARCHAR(40) NOT NULL, 
	historical_theme_id VARCHAR(36), 
	historical_similarity_score FLOAT, 
	merged_into_theme_id VARCHAR(36), 
	approved_by VARCHAR(128), 
	approved_at TIMESTAMP WITH TIME ZONE, 
	rejected_at TIMESTAMP WITH TIME ZONE, 
	rejection_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(historical_theme_id) REFERENCES historical_themes (id) ON DELETE SET NULL, 
	FOREIGN KEY(merged_into_theme_id) REFERENCES themes (id) ON DELETE SET NULL
);

CREATE INDEX ix_themes_status ON themes (status);

CREATE INDEX ix_themes_analysis_run_id ON themes (analysis_run_id);


CREATE TABLE workflow_logs (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36), 
	request_id VARCHAR(64), 
	event_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	step VARCHAR(80), 
	duration_ms INTEGER, 
	metadata_json JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_workflow_logs_request_id ON workflow_logs (request_id);

CREATE INDEX ix_workflow_logs_event_type ON workflow_logs (event_type);

CREATE INDEX ix_workflow_logs_analysis_run_id ON workflow_logs (analysis_run_id);


CREATE TABLE report_theme_snapshots (
	id VARCHAR(36) NOT NULL, 
	report_id VARCHAR(36) NOT NULL, 
	original_theme_id VARCHAR(36) NOT NULL, 
	theme_title VARCHAR(240) NOT NULL, 
	summary TEXT NOT NULL, 
	problem_statement TEXT NOT NULL, 
	pattern_type VARCHAR(30) NOT NULL, 
	metrics_json JSON NOT NULL, 
	evidence_json JSON NOT NULL, 
	historical_comparison_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_id) REFERENCES reports (id) ON DELETE CASCADE
);

CREATE INDEX ix_report_theme_snapshots_report_id ON report_theme_snapshots (report_id);


CREATE TABLE theme_feedback (
	theme_id VARCHAR(36) NOT NULL, 
	feedback_item_id VARCHAR(36) NOT NULL, 
	membership_score FLOAT NOT NULL, 
	is_primary_evidence BOOLEAN NOT NULL, 
	assigned_by VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (theme_id, feedback_item_id), 
	FOREIGN KEY(theme_id) REFERENCES themes (id) ON DELETE CASCADE, 
	FOREIGN KEY(feedback_item_id) REFERENCES feedback_items (id) ON DELETE CASCADE
);


CREATE TABLE theme_review_actions (
	id VARCHAR(36) NOT NULL, 
	analysis_run_id VARCHAR(36) NOT NULL, 
	theme_id VARCHAR(36) NOT NULL, 
	action_type VARCHAR(40) NOT NULL, 
	before_state JSON NOT NULL, 
	after_state JSON NOT NULL, 
	performed_by VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(analysis_run_id) REFERENCES analysis_runs (id) ON DELETE CASCADE, 
	FOREIGN KEY(theme_id) REFERENCES themes (id) ON DELETE CASCADE
);

CREATE INDEX ix_theme_review_actions_analysis_run_id ON theme_review_actions (analysis_run_id);

CREATE INDEX ix_theme_review_actions_theme_id ON theme_review_actions (theme_id);

COMMIT;
