# Experimental D2D Communication System for LoRa Networks

## Overview

This repository contains the experimental implementation and evaluation of a Device-to-Device (D2D) communication system using LoRa technology.

The project was developed during a **Summer Internship at the Indian Institute of Technology Bhubaneswar (IIT Bhubaneswar)**.

The implementation is inspired by the research work:

> **Accelerating Update Broadcasts Over LoRaWAN Downlink via D2D Cooperation**  
> Anshika Singh and Siddhartha S. Borkotoky  
> IEEE Transactions on Industrial Informatics, Vol. 22, No. 6, June 2026.

The objective of this project is to experimentally investigate and evaluate the feasibility of D2D-assisted communication using a real-world multi-node LoRa setup.

---

## Objective

LoRaWAN networks face limitations in downlink communication due to factors such as duty-cycle restrictions, limited gateway transmission capacity, and long communication delays.

The referenced research proposes Device-to-Device (D2D) cooperation, where nearby devices assist in forwarding update packets to other nodes.

This project focuses on experimentally implementing and evaluating this concept using physical hardware.

The main objectives are:

- Implement a multi-node LoRa-based communication system.
- Establish D2D communication between distributed nodes.
- Implement packet forwarding using helper nodes.
- Evaluate packet transmission and reception performance.
- Study the practical feasibility of cooperative communication.
- Analyze the behavior of the system under real-world experimental conditions.

---

## System Architecture

The experimental setup consists of four primary nodes:

- Transmitter
- Helper Node 1
- Helper Node 2
- Receiver

```text
                    ┌─────────────────┐
                    │   Transmitter   │
                    │  (Source Node)  │
                    └────────┬────────┘
                             │
                         LoRa Link
                             │
              ┌──────────────┴──────────────┐
              │                             │
      ┌───────▼────────┐           ┌────────▼────────┐
      │ Helper Node 1  │           │ Helper Node 2   │
      │    (Relay)     │           │    (Relay)      │
      └───────┬────────┘           └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                       D2D Communication
                             │
                    ┌────────▼────────┐
                    │    Receiver     │
                    │ (Destination)   │
                    └─────────────────┘
