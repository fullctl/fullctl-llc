# Changelog


## Unreleased
### Added
- task queue health checks
### Fixed
- select2 background color issue


## 1.12.0
### Added
- slug model / serializer mixins
- extendible health check
- no_button_center modal type
- continue_center modal type
### Fixed
- auth redirect in standalone auth mode
- fixes issue with meta data cache expiry if expiry was set to never and api throttling was encountered


## 1.11.0
### Added
- adds django-cors-headers to the project and the django default settings
### Fixed
- excessive database queries when qualifying tasks
- visual issues with the org selection menu


## 1.10.0
### Added
- support for django 4.2
- service bridge data views now expose a `limit` parameter to the request url
### Fixed
- task concurrency errors
- bug with blocking task qualifiers that could cause task execution to happen out of order


## 1.9.0
### Added
- API schema tools


## 1.8.0
### Added
- ux tweaks to improve readability and usability
### Fixed
- OpenAPI schema generation issues
- issues with tab from URL not being selected


## 1.7.0
### Added
- python 3.12
### Fixed
- css for chrome background
### Removed
- python 3.8 support


## 1.6.0
### Added
- per ix billing
- Devicectl referee reports (#183)
### Fixed
- dont remake aggregated graphs every attempt (#177)


## 1.5.0
### Added
- rrd support
- image graphs
### Fixed
- UI fixes
### Changed
- bring dockerfile in line with tasks


## 1.4.0
### Removed
- support for python 3.7


## 1.3.0
### Added
- healthcheck URL for base services
- auditctl support
### Fixed
- metadata issues
- url_join with ints
- task ConcurrencyLimit qualifier
### Changed
- UI updates


## 1.2.0
### Added
- contact form interface


## 1.0.0
### Added
- all 1.0 changes!
- pdbctl service bridge
- pdbctl integration
- support for python 3.11
### Removed
- support for python 3.6


## 0.3.0
### Added
- asn autocomplete lookup from peering db data


## 0.2.0
### Fixed
- import errors from splitting out fullctl core


## 0.1.1
### Fixed
- import error in task_interface.py


## 0.1.0
### Added
- initial release