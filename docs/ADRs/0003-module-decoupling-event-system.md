# 3. Module Decoupling with Event-Driven Architecture

Date: 2025-04-03

## Status

Accepted

## Context

The Dewey project currently has several core modules (crm, research, bookkeeping, llm) that interact directly with each other, creating tight coupling. This has led to several issues:

1. Direct dependencies between modules make it difficult to change one module without affecting others
2. Testing individual modules requires mocking complex dependencies
3. Adding new features that span multiple modules requires changes across the codebase
4. Module boundaries are not clearly defined, leading to potential circular dependencies

We need to establish a more maintainable architecture that allows modules to evolve independently while still enabling cross-module functionality.

## Decision

We will implement an event-driven architecture with the following components:

1. **Central Event Bus**: Create a `dewey.core.events.event_bus` module that provides publish-subscribe functionality
2. **Interface Abstractions**: Define clear interface contracts for module services in `dewey.core.interfaces`
3. **Dependency Injection**: Enhance `BaseScript` to support dependency injection for services
4. **Service Registry**: Implement a service registry for locating and instantiating service implementations

The event-driven approach will allow modules to communicate without direct dependencies. For example, when the CRM module discovers a new contact, it will publish an event that other modules can subscribe to, rather than calling their functions directly.

## Consequences

### Positive

- **Reduced Coupling**: Modules will depend on interfaces and events rather than concrete implementations
- **Improved Testability**: Services can be mocked independently for testing
- **Flexibility**: New features can be added by subscribing to existing events
- **Clear Boundaries**: Module responsibilities will be more clearly defined
- **Scalability**: Event-driven architecture supports future distributed processing

### Negative

- **Initial Refactoring Cost**: Significant work to refactor existing code to use the new approach
- **Complexity**: Event-driven systems can be harder to debug and trace execution flow
- **Learning Curve**: Team members will need to understand the new patterns
- **Potential Performance Impact**: Indirect communication via events may add minimal overhead

## Implementation Plan

1. **Phase 1: Core Infrastructure**
   - Create the event bus implementation
   - Define key interfaces for core services
   - Update BaseScript to support dependency injection

2. **Phase 2: Module Adaptation**
   - Refactor each module to use events for cross-module communication
   - Implement service interfaces for each module
   - Update documentation and examples

3. **Phase 3: Testing & Validation**
   - Develop comprehensive tests for the new architecture
   - Measure performance impact and optimize if needed
   - Create examples of cross-module features using the new approach

We will start with prioritizing the `dewey.core.events` module implementation, focusing on the core event bus functionality. After that, we'll address the highest priority cross-module interactions identified through codebase analysis. 