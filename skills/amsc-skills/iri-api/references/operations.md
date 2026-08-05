# IRI API Operations

Generated from `openapi.json`.

Columns:
- `operationId`: OpenAPI operation identifier
- `auth`: `public` or `auth` based on operation security metadata
- `required_params`: required path/query parameters
- `body`: request content types if request body is supported

| operationId | method | path | auth | required_params | body |
|---|---|---|---|---|---|
| getCapabilities | GET | `/api/v1/account/capabilities` | public |  |  |
| getCapability | GET | `/api/v1/account/capabilities/{capability_id}` | public | capability_id |  |
| getEventByIncident | GET | `/api/v1/status/events/{event_id}` | public | event_id |  |
| getEventsByIncident | GET | `/api/v1/status/events` | public |  |  |
| getFacility | GET | `/api/v1/facility` | public |  |  |
| getIncident | GET | `/api/v1/status/incidents/{incident_id}` | public | incident_id |  |
| getIncidents | GET | `/api/v1/status/incidents` | public |  |  |
| getResource | GET | `/api/v1/status/resources/{resource_id}` | public | resource_id |  |
| getResources | GET | `/api/v1/status/resources` | public |  |  |
| getSite | GET | `/api/v1/facility/sites/{site_id}` | public | site_id |  |
| getSites | GET | `/api/v1/facility/sites` | public |  |  |
| cancelJob | DELETE | `/api/v1/compute/cancel/{resource_id}/{job_id}` | auth | resource_id,job_id |  |
| checksum | GET | `/api/v1/filesystem/checksum/{resource_id}` | auth | resource_id,path |  |
| chmod | PUT | `/api/v1/filesystem/chmod/{resource_id}` | auth | resource_id | application/json |
| chown | PUT | `/api/v1/filesystem/chown/{resource_id}` | auth | resource_id | application/json |
| compress | POST | `/api/v1/filesystem/compress/{resource_id}` | auth | resource_id | application/json |
| cp | POST | `/api/v1/filesystem/cp/{resource_id}` | auth | resource_id | application/json |
| deleteTask | DELETE | `/api/v1/task/{task_id}` | auth | task_id |  |
| download | GET | `/api/v1/filesystem/download/{resource_id}` | auth | resource_id,path |  |
| extract | POST | `/api/v1/filesystem/extract/{resource_id}` | auth | resource_id | application/json |
| file | GET | `/api/v1/filesystem/file/{resource_id}` | auth | resource_id,path |  |
| getJob | GET | `/api/v1/compute/status/{resource_id}/{job_id}` | auth | resource_id,job_id |  |
| getJobs | POST | `/api/v1/compute/status/{resource_id}` | auth | resource_id | application/json |
| getProject | GET | `/api/v1/account/projects/{project_id}` | auth | project_id |  |
| getProjectAllocationByProject | GET | `/api/v1/account/projects/{project_id}/project_allocations/{project_allocation_id}` | auth | project_id,project_allocation_id |  |
| getProjectAllocationsByProject | GET | `/api/v1/account/projects/{project_id}/project_allocations` | auth | project_id |  |
| getProjects | GET | `/api/v1/account/projects` | auth |  |  |
| getTask | GET | `/api/v1/task/{task_id}` | auth | task_id |  |
| getTasks | GET | `/api/v1/task` | auth |  |  |
| getUserAllocationByProjectAllocation | GET | `/api/v1/account/projects/{project_id}/project_allocations/{project_allocation_id}/user_allocations/{user_allocation_id}` | auth | project_id,project_allocation_id,user_allocation_id |  |
| getUserAllocationsByProjectAllocation | GET | `/api/v1/account/projects/{project_id}/project_allocations/{project_allocation_id}/user_allocations` | auth | project_id,project_allocation_id |  |
| head | GET | `/api/v1/filesystem/head/{resource_id}` | auth | resource_id,path |  |
| launchJob | POST | `/api/v1/compute/job/{resource_id}` | auth | resource_id | application/json |
| ls | GET | `/api/v1/filesystem/ls/{resource_id}` | auth | resource_id,path |  |
| mkdir | POST | `/api/v1/filesystem/mkdir/{resource_id}` | auth | resource_id | application/json |
| mv | POST | `/api/v1/filesystem/mv/{resource_id}` | auth | resource_id | application/json |
| rm | DELETE | `/api/v1/filesystem/rm/{resource_id}` | auth | resource_id,path |  |
| stat | GET | `/api/v1/filesystem/stat/{resource_id}` | auth | resource_id,path |  |
| symlink | POST | `/api/v1/filesystem/symlink/{resource_id}` | auth | resource_id | application/json |
| tail | GET | `/api/v1/filesystem/tail/{resource_id}` | auth | resource_id,path |  |
| updateJob | PUT | `/api/v1/compute/job/{resource_id}/{job_id}` | auth | resource_id,job_id | application/json |
| upload | POST | `/api/v1/filesystem/upload/{resource_id}` | auth | resource_id,path | multipart/form-data |
| view | GET | `/api/v1/filesystem/view/{resource_id}` | auth | resource_id,path |  |
