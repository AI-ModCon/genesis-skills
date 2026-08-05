When completing this template:

* Prefer actual technologies, products, protocols, services, and data formats over generic language whenever that information is relevant.
* Preserve the application's functional behavior, trust boundaries, and security-relevant capabilities.
* Distinguish between what the application **can**, **cannot**, and **must not** do.
* Name concrete systems (e.g., "PostgreSQL", "REST API", "Salesforce", "OPC UA") when preparing an internal fingerprint.
* Replace implementation-specific names with functional categories (e.g., "relational database", "industrial control protocol", "CRM platform") only when creating a generalized or publicly shareable example.
* Avoid unnecessary implementation details that do not materially affect the application's security posture (such as internal project names, file paths, or organization-specific terminology).

---

# Application Purpose

**Author guidance:** Describe the application's primary mission in one or two paragraphs. Name the actual domain, users, and operational context when known. If producing a public example, replace organization- or product-specific details with the closest functional description.

This application is an AI-assisted operations platform that helps users monitor, analyze, and interact with complex systems through approved interfaces. It provides intelligent assistance for operational workflows, decision support, diagnostics, and controlled execution of actions while enforcing validation, safety constraints, and human oversight.

---

# Key Features and Capabilities

**Author guidance:** List the application's major capabilities. Prefer concrete technologies, protocols, or services (for example, "REST APIs", "OPC UA", "PostgreSQL", "SharePoint", "AWS S3") over generic descriptions when those details are relevant.

Examples of capabilities include:

* Multi-step planning and task orchestration
* Iterative reasoning and tool use
* Access to external systems through approved interfaces
* Read and/or write operations against managed resources
* Historical data retrieval
* Search and discovery over structured metadata
* Code execution for analysis or automation
* Report, visualization, or artifact generation
* Policy validation before executing actions
* Human approval workflows
* Verification of completed operations

---

# Industry / Domain

**Author guidance:** Describe the operational domain with enough specificity for someone unfamiliar with the application to understand its environment.

Examples include:

* Scientific research infrastructure
* Manufacturing
* Healthcare
* Energy systems
* Financial services
* Enterprise IT
* Software engineering
* Laboratory automation
* Cloud infrastructure

---

# System Rules and Constraints

**Author guidance:** Document behavioral rules that should always hold, regardless of user requests.

Examples include:

1. Never invent identifiers, records, or resources.
2. Obtain current state before recommending or performing modifications.
3. Verify completed changes using approved mechanisms.
4. Respect configured policies and operational limits.
5. Never fabricate analysis results or measurements.
6. Use only approved interfaces when interacting with external systems.
7. Report failures instead of silently substituting unsupported approaches.
8. Preserve audit records and operational history.
9. Flag generated code that performs high-impact actions before execution.
10. Require additional validation for designated sensitive operations.

---

# Systems and Data the Application Has Access To

**Author guidance:** Enumerate the major systems, services, repositories, and execution environments the application can access. Use actual technology names whenever practical.

Possible entries include:

* <Operational control system>
* <Business application>
* <REST or GraphQL API>
* <Industrial control protocol>
* <Time-series database or historian>
* <Relational database>
* <Document repository>
* <Search index>
* <Vector database>
* <Cloud object storage>
* <Message queue>
* <Execution environment>
* <Filesystem or workspace storage>
* <Simulation or testing environment>

Examples of technologies (replace with actual ones if applicable):

* PostgreSQL
* Elasticsearch
* Kafka
* SharePoint
* GitHub
* Azure Blob Storage
* OPC UA
* MQTT
* Kubernetes

---

# Systems and Data the Application Should NOT Have Access To

**Author guidance:** Describe important trust boundaries and explicitly identify systems that remain outside the application's authority.

Common examples include:

* Identity providers
* Authentication credential stores
* Cryptographic key management systems
* Safety-critical control systems
* Administrative operating system configuration
* Infrastructure management platforms
* Other users' private workspaces
* Production databases outside approved scope
* Internal implementation details
* Security monitoring infrastructure

---

# Types of Users Who Interact with the Application

**Author guidance:** Describe real user populations rather than generic job titles whenever possible.

Examples include:

* Operators
* Engineers
* Researchers
* Analysts
* Administrators
* Developers
* Customer support personnel
* Scientists
* Maintenance technicians
* Domain specialists

For each user type, briefly describe typical interactions if they differ significantly.

---

# Security and Compliance Requirements

**Author guidance:** Describe the policies, regulations, governance requirements, or architectural principles that constrain application behavior.

Examples include:

* Organizational security policies
* Industry regulatory requirements
* Audit logging
* Human approval requirements
* Least privilege
* Separation of duties
* Data integrity guarantees
* Change management
* Operational safety requirements
* Record retention policies

---

# Types of Sensitive Data Handled

**Author guidance:** Be specific about the data the application processes. Group similar categories together.

Possible categories include:

* Operational telemetry
* Configuration information
* Customer or user records
* Intellectual property
* Source code
* Research data
* Financial information
* Personally identifiable information
* Authentication tokens
* Security policies
* Proprietary business information
* Operational procedures

---

# Example Data Identifiers and Formats

**Author guidance:** Provide representative examples of identifiers, schemas, file formats, and data structures used by the application. Prefer realistic examples over abstract descriptions.

Examples:

**Resource identifiers**

```
<system>:<component>:<resource>:<attribute>
```

```
device.region.parameter
```

```
service/environment/resource-id
```

**Structured records**

```
resource_id
timestamp
value
status
quality
```

**Configuration**

```
minimum_value
maximum_value
allowed_operations
verification_mode
approval_required
```

**Common data formats**

* JSON
* YAML
* XML
* CSV
* Parquet
* SQL tables
* Markdown
* Time-series datasets
* Binary scientific formats
* Images
* PDFs

---

# Critical or Dangerous Actions the Application Can Perform

**Author guidance:** Focus on actions whose misuse could affect confidentiality, integrity, availability, financial assets, safety, or physical systems.

Examples include:

* Modifying production configuration
* Updating operational parameters
* Executing generated code
* Running automated workflows
* Coordinating multi-system operations
* Deleting or overwriting data
* Accessing sensitive operational information
* Triggering external services
* Deploying software
* Creating or modifying infrastructure
* Initiating physical processes

---

# Content and Topics the Application Should Never Discuss

**Author guidance:** Document prohibited assistance, particularly around bypassing safeguards or abusing system capabilities.

Examples include:

* Circumventing safety controls
* Evading security monitoring
* Bypassing authorization
* Fabricating operational data
* Modifying audit records
* Privilege escalation techniques
* Unauthorized resource discovery
* Disabling validation mechanisms
* Concealing malicious activity
* Presenting speculation as verified system information

---

# Red Team User Persona

**Author guidance:** Describe realistic adversaries who might interact directly with the application. Focus on goals rather than implementation details.

Example persona:

An authorized user, compromised account, or external attacker who attempts to:

* Obtain information beyond their authorized access
* Circumvent application policies or safeguards
* Escalate privileges
* Abuse automation capabilities
* Manipulate analyses or recommendations
* Extract sensitive or proprietary information
* Execute unauthorized operations
* Exploit generated code or tool integrations
* Interfere with auditing or accountability
* Cause operational, financial, reputational, or physical harm
