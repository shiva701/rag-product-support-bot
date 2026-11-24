# Shiva Shukla Resume

## Summary
Shiva Shukla is a Full Stack Software Engineer with 6+ years of experience building scalable,
secure backend systems in Java (Spring Boot, WebFlux) and Python (FastAPI) with SQL/NoSQL data
layers, and accessible front ends in TypeScript, React, and Lit, deployed on Kubernetes (AKS)
with Docker, Helm, and Terraform. Shiva has supported high-availability production systems with
OpenTelemetry, Datadog, and Prometheus, and built AI-powered features with MCP servers, AI agents,
and LLMs. Shiva uses AI-assisted development tools to ship faster in Agile teams, and has a strong
foundation in data structures, algorithms, and design patterns.

## Most Recent Role and Job Title
Shiva Shukla's most recent job title is Software Engineer Specialist at PTC Inc. in Wayne, PA,
held from Feb 01 2026 to Nov 20 2026. Before that promotion, Shiva was an Associate Software Engineer at PTC Inc. from Aug 28 2023 to Jan 31 2026. Shiva's first job was at GlobalLogic, where Shiva's last position was Senior Software Engineer.

## Career Timeline
Shiva Shukla's roles, most recent first:
- PTC Inc., Software Engineer Specialist, Wayne, PA: Feb 01 2026 - Nov 20 2026.
- PTC Inc., Associate Software Engineer, Wayne, PA: Aug 28 2023 - Jan 31 2026.
- George Mason University, Master of Science in Computer Science: Aug 23 2021 - May 19 2023.
- GlobalLogic, Senior Software Engineer, Noida, India: Jul 05 2018 - Aug 06 2021.
  - Promoted from Associate Software Engineer to Software Engineer, then to Senior Software Engineer.
- Harcourt Butler Technological Institute, Bachelor of Technology in Information Technology: Aug 04 2014 - Jun 30 2018.
Shiva has worked at two companies: PTC Inc. (two roles, Aug 28 2023 - Nov 20 2026) and GlobalLogic (three roles, Jul 05 2018 - Aug 06 2021).
The most recent job title is Software Engineer Specialist at PTC Inc.

## PTC Inc. - Software Engineer Specialist (Feb 01 2026 - Nov 20 2026)
Role: Software Engineer Specialist at PTC Inc., Wayne, PA, from Feb 01 2026 to Nov 20 2026.
Full-stack work with Python, Java, TypeScript, Lit, Azure, and SQL. This is Shiva's most recent role.
- Built an Azure-based FastMCP gateway that exposes registered agent tools via JSON-RPC 2.0 and REST APIs, with OAuth2/JWT, request validation, and standardized error handling. Added Redis and in-memory caching for an Azure Storage registry to improve agent discovery and routing.
- Instrumented FastAPI services with OpenTelemetry (traces, metrics, logs) exporting to Datadog and Prometheus for SLA/SLO alerting, with trace-log correlation, a circuit breaker on the async export queue, and a telemetry health monitoring REST API.
- Automated CI/CD pipelines using GitHub Actions and GitLab with reusable components, integrating HashiCorp Vault, Wiz, Black Duck, Invicti, and Checkmarx, and deploying services on Azure Kubernetes using Helm charts and pre- and post-deployment tests.
- Provisioned Azure infrastructure (AKS, Storage, Redis) as code with reusable Terraform modules in GitLab, cutting environment setup time by 20% and eliminating config drift across environments.
- Obfuscated 10+ core LLM algorithms using Cython to secure intellectual property for a private SaaS deployment, keeping latency within 3% of the Python baseline.

## PTC Inc. - Associate Software Engineer (Aug 28 2023 - Jan 31 2026)
Role: Associate Software Engineer at PTC Inc., Wayne, PA, from Aug 28 2023 to Jan 31 2026.
Full-stack work with Python, Java, TypeScript, Lit, Azure, and SQL.
- Designed and developed localized, WAI-ARIA-compliant TypeScript and Lit web components for the Requirement Assistant (RA) AI tool in a software project management application, increasing accessibility by 50%.
- Leveraged AI-assisted development tools (GitHub Copilot, Claude) to generate and debug test suites, increasing RA test coverage from 30% to 80% using Playwright, JUnit, and Pytest, with containerized integration tests.
- Developed the RA AI tool plugin using Java, OOP, Spring Boot, REST APIs, Gradle, OAuth2/JWT, Tomcat, and Postgres to mediate communication between the web component and backend LLM services, improving request processing throughput by 25%.
- Secured the RA AI tool plugin with Spring Security (OAuth2/JWT) and token rotation policies, reducing unauthorized requests by 15%.
- Co-developed a FastAPI application using LangChain and OpenAI LLMs to evaluate and rewrite software requirements as per INCOSE standards, reducing token costs by 25% and improving F1 score by 22% through prompt optimization.
- Integrated an API in the RA plugin to send API metadata to Snowflake for faster failure triage.
- Optimized stored procedures in a MySQL database, improving the GET API performance by 30%.
- Utilized ThingWorx, JavaScript, Java, Spring Boot, RabbitMQ, and Azure to build a production-cycle analytics product with machine learning models that forecast output and detect the impact of equipment failures and machine faults, improving accuracy by 18%.

## GlobalLogic - Senior Software Engineer (Jul 05 2018 - Aug 06 2021)
Role: Senior Software Engineer at GlobalLogic, Noida, India, from Jul 05 2018 to Aug 06 2021.
Promotions: joined as an Associate Software Engineer, promoted to Software Engineer, then to Senior Software Engineer.
Backend engineering with Java, Spring Boot, Spring WebFlux, and NoSQL.
- Developed REST APIs for a learning platform using Java, Spring Boot, Reactive Streams, Kafka, and the Couchbase NoSQL database; added unit tests with JUnit, Mockito, and StepVerifier, improving code quality by 35% and test coverage by 40%.
- Implemented Kafka with Spring Cloud Streams API and a retry mechanism to improve microservice reliability by 30%.
- Optimized Couchbase N1QL queries with composite indexes, improving lookup by 25% across 5 high-traffic REST endpoints.
- Authored consumer contracts using Spring Cloud Contracts, reducing early requirement gaps by 20%.

## Requirement Assistant (RA) AI Tool
The Requirement Assistant (RA) is an AI tool Shiva worked on at PTC Inc., inside a software
project management application. It evaluates and rewrites software requirements as per
INCOSE standards. Shiva built it as an Associate Software Engineer at PTC Inc. (Aug 28 2023 - Jan 31 2026).
Shiva's contributions:
- Front end: localized, WAI-ARIA-compliant TypeScript and Lit web components (accessibility up 50%).
- Plugin: Java, Spring Boot, REST APIs, Gradle, Tomcat, and Postgres plugin that mediates between the web component and backend LLM services (throughput up 25%).
- LLM service: FastAPI application using LangChain and OpenAI LLMs (token costs down 25%, F1 score up 22% through prompt optimization).
- Security: Spring Security with OAuth2/JWT and token rotation policies (unauthorized requests down 15%).
- Testing: coverage raised from 30% to 80% with Playwright, JUnit, Pytest, and containerized integration tests, using GitHub Copilot and Claude to generate and debug the test suites.
- Operations: API metadata sent to Snowflake for faster failure triage.

## AI, LLM, and Agent Experience
Shiva's AI skills: Model Context Protocol (MCP), FastMCP, AI Agents, LangChain, LLMs,
Prompt Engineering, Claude, and GitHub Copilot.
- Built an Azure-based FastMCP gateway exposing registered agent tools via JSON-RPC 2.0 and REST APIs, with caching for agent discovery and routing (PTC Inc.).
- Co-developed a FastAPI application using LangChain and OpenAI LLMs to evaluate and rewrite software requirements, reducing token costs by 25% and improving F1 score by 22% through prompt optimization (PTC Inc.).
- Obfuscated 10+ core LLM algorithms using Cython for a private SaaS deployment, keeping latency within 3% of the Python baseline (PTC Inc.).
- Used AI-assisted development tools (GitHub Copilot, Claude Code) to generate and debug test suites, raising RA test coverage from 30% to 80% (PTC Inc.).

## Skills: Languages and Frameworks
Languages: Java, Python, JavaScript, TypeScript, SQL, HTML5, CSS, React.
Frameworks: Hibernate, Spring Boot, Spring Cloud, JUnit, Mockito, TestNG, ShellSpec, Lit, Playwright, FastAPI.

## Skills: Cloud, DevOps, and Tools
Cloud: Azure Kubernetes Service (AKS), Azure Storage, and AWS (S3, EC2, RDS, DynamoDB, Lambda, CloudWatch).
Tools and technologies: GitLab, Jenkins, Git, Docker, Kubernetes, Apache Tomcat, Kafka, Zookeeper, Maven, Gradle, Agile, Linux, Microservices, Helm, Terraform, OpenTelemetry, Prometheus, Datadog, Snowflake, RESTful APIs, Swagger, GitHub Actions, Node.js.

## Skills: Databases
Couchbase, MySQL, PostgreSQL, and Redis.
Shiva optimized Couchbase N1QL queries with composite indexes at GlobalLogic, optimized MySQL
stored procedures and used Postgres at PTC Inc., and added Redis caching to the FastMCP gateway.

## Skills: Security
OAuth2, JWT, Spring Security, HashiCorp Vault, Wiz, Black Duck, Checkmarx, Invicti, and SonarQube.
Shiva secured APIs and plugins with OAuth2/JWT and token rotation, and integrated HashiCorp Vault, Wiz, Black Duck, Invicti, and Checkmarx security scanning into CI/CD pipelines.

## Skills: AI
Model Context Protocol (MCP), FastMCP, LangChain, LLM, LangGraph, Retrieval-Augmented Generation (RAG), Vector Search, Embeddings, AI Agents, Prompt Engineering, Claude Code, GitHub Copilot

## Education
- George Mason University, Fairfax, VA: Master of Science in Computer Science, Aug 23 2021 - May 19 2023, GPA 3.93.
- Harcourt Butler Technological Institute, Kanpur, India: Bachelor of Technology in Information Technology, Aug 04 2014 - Jun 30 2018, GPA 3.8.
Shiva's highest degree is the Master of Science in Computer Science from George Mason University.

## Contact and Links
- LinkedIn: linkedin.com/in/shivashuklagmu
- Portfolio: shiva701.github.io/Portfolio/
- GitHub: github.com/shiva701
For anything not covered here, contact Shiva directly through LinkedIn or GitHub.
