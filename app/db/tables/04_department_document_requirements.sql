-- Which documents a department needs before a visit, per visit type.

CREATE TABLE department_document_requirements (
  id            bigserial PRIMARY KEY,
  department_id bigint NOT NULL REFERENCES departments(id),
  visit_type    visit_type NOT NULL,
  document_type document_type NOT NULL,
  max_age_days  int,                           -- NULL means any age
  mandatory     boolean NOT NULL DEFAULT true,
  UNIQUE (department_id, visit_type, document_type)
);
