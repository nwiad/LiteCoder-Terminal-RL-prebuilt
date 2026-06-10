#!/usr/bin/env python3
"""Generate 200 synthetic CS paper abstracts across 6 domains."""
import json
import random
import os

random.seed(42)

DOMAINS = {
    "machine_learning": {
        "titles": [
            "Gradient-Based Optimization for Deep Neural Networks",
            "Bayesian Approaches to Hyperparameter Tuning",
            "Transfer Learning in Low-Resource Settings",
            "Ensemble Methods for Robust Classification",
            "Attention Mechanisms in Sequence Models",
            "Federated Learning with Differential Privacy",
            "Neural Architecture Search via Reinforcement Learning",
            "Self-Supervised Representation Learning",
            "Graph Neural Networks for Molecular Property Prediction",
            "Meta-Learning for Few-Shot Classification",
        ],
        "phrases": [
            "we propose a novel deep learning framework that improves training efficiency",
            "our method leverages gradient descent optimization with momentum",
            "the model achieves state-of-the-art accuracy on benchmark datasets",
            "we introduce a regularization technique to prevent overfitting in deep networks",
            "experiments demonstrate improved generalization performance across tasks",
            "the neural network architecture incorporates skip connections and residual blocks",
            "we employ batch normalization and dropout for training stability",
            "our approach uses backpropagation with adaptive learning rates",
            "the loss function combines cross-entropy with contrastive learning terms",
            "we evaluate on CIFAR and ImageNet classification benchmarks",
            "transfer learning from pretrained models significantly reduces training time",
            "the attention mechanism captures long-range dependencies in sequential data",
            "we analyze convergence properties of the stochastic optimization algorithm",
            "data augmentation strategies improve model robustness to distribution shift",
            "the embedding space captures semantic similarity between input samples",
        ],
    },
    "networking": {
        "titles": [
            "Software-Defined Networking for Data Center Optimization",
            "Low-Latency Routing Protocols for 5G Networks",
            "Congestion Control in High-Bandwidth Networks",
            "Network Function Virtualization Architecture Design",
            "Quality of Service Guarantees in Cloud Networks",
            "Peer-to-Peer Content Distribution Networks",
            "TCP Performance Analysis in Wireless Networks",
            "Load Balancing Strategies for Distributed Systems",
            "Network Intrusion Detection Using Flow Analysis",
            "Edge Computing for IoT Network Optimization",
        ],
        "phrases": [
            "we present a novel routing protocol for software-defined networks",
            "our approach reduces end-to-end latency in data center network topologies",
            "the algorithm optimizes bandwidth allocation across network links",
            "we analyze packet loss rates under varying traffic load conditions",
            "the protocol achieves high throughput with minimal control overhead",
            "network virtualization enables flexible and dynamic resource management",
            "we evaluate performance using real-world network traffic traces",
            "the congestion control mechanism adapts to changing network conditions",
            "our system supports quality of service guarantees for critical traffic flows",
            "the architecture scales to thousands of concurrent network connections",
            "we implement flow-based traffic classification at line rate speed",
            "the load balancer distributes incoming requests across multiple backend servers",
            "network telemetry data enables proactive fault detection and mitigation",
            "the protocol stack supports both IPv4 and IPv6 addressing schemes",
            "we measure round-trip time and jitter across diverse network paths",
        ],
    },
    "databases": {
        "titles": [
            "Query Optimization in Distributed Database Systems",
            "Indexing Strategies for Time-Series Data Storage",
            "Transaction Processing in NewSQL Databases",
            "Graph Database Query Languages and Optimization",
            "Data Partitioning for Scalable Analytics Platforms",
            "Approximate Query Processing with Error Bounds",
            "Columnar Storage Engines for Analytical Workloads",
            "Concurrency Control in Multi-Version Databases",
            "Stream Processing with Exactly-Once Semantics",
            "Database Migration Strategies for Cloud Environments",
        ],
        "phrases": [
            "we propose an efficient query optimization strategy for distributed databases",
            "our indexing technique reduces query latency by an order of magnitude",
            "the storage engine supports both OLTP and OLAP workloads efficiently",
            "we implement a novel concurrency control protocol for high contention scenarios",
            "the system achieves strong consistency with minimal coordination overhead",
            "our approach partitions data across nodes for parallel query execution",
            "the query planner uses cost-based optimization with table statistics",
            "we evaluate throughput and latency on standard TPC benchmark workloads",
            "the transaction manager supports serializable isolation levels",
            "our columnar format achieves high compression ratios for analytical data",
            "the buffer pool management strategy minimizes disk I/O operations",
            "we support SQL queries with joins across distributed table partitions",
            "the write-ahead log ensures durability and crash recovery guarantees",
            "our system handles schema evolution without requiring downtime",
            "the caching layer reduces repeated query execution costs significantly",
        ],
    },
    "security": {
        "titles": [
            "Adversarial Attack Detection in Neural Networks",
            "Privacy-Preserving Data Sharing Protocols",
            "Blockchain-Based Access Control Systems",
            "Vulnerability Detection Using Static Analysis Tools",
            "Secure Multi-Party Computation Frameworks",
            "Intrusion Detection with Anomaly-Based Methods",
            "Homomorphic Encryption for Cloud Computing",
            "Authentication Protocols for IoT Devices",
            "Malware Classification Using Behavioral Analysis",
            "Zero-Trust Architecture for Enterprise Networks",
        ],
        "phrases": [
            "we present a defense mechanism against adversarial perturbation attacks",
            "our protocol ensures data privacy through differential privacy guarantees",
            "the system detects malicious network traffic using anomaly detection methods",
            "we implement secure computation without revealing private input data",
            "the encryption scheme supports arithmetic operations on encrypted data",
            "our approach identifies software vulnerabilities through automated static analysis",
            "the authentication protocol resists replay and man-in-the-middle attacks",
            "we evaluate detection accuracy on real-world malware sample datasets",
            "the access control model enforces least-privilege security principles",
            "our framework provides end-to-end encryption for data in transit",
            "the intrusion detection system achieves low false positive rates",
            "we analyze the security properties of the proposed cryptographic protocol",
            "the blockchain ledger provides tamper-evident audit trails for transactions",
            "our method classifies malware families based on behavioral feature analysis",
            "the zero-trust model verifies every access request independently",
        ],
    },
    "computer_vision": {
        "titles": [
            "Object Detection in Autonomous Driving Scenarios",
            "Semantic Segmentation of Medical Images",
            "Image Super-Resolution Using Generative Models",
            "Visual Question Answering with Multimodal Fusion",
            "3D Point Cloud Processing for Scene Understanding",
            "Face Recognition Under Occlusion Conditions",
            "Video Action Recognition with Temporal Modeling",
            "Optical Flow Estimation Using Deep Networks",
            "Image Captioning with Attention-Based Decoders",
            "Domain Adaptation for Cross-Dataset Object Detection",
        ],
        "phrases": [
            "we propose a convolutional neural network architecture for object detection",
            "our model performs pixel-wise semantic segmentation of medical images",
            "the generative adversarial network produces high-resolution image outputs",
            "we combine visual and textual features for multimodal scene understanding",
            "the architecture processes 3D point clouds for accurate scene reconstruction",
            "our method achieves robust face recognition under partial occlusion conditions",
            "the temporal model captures motion patterns across consecutive video frames",
            "we estimate dense optical flow fields between consecutive image frames",
            "the decoder generates natural language descriptions of visual image content",
            "our approach handles domain shift between training and test image datasets",
            "the feature pyramid network extracts multi-scale visual representations",
            "we use data augmentation including random cropping and horizontal flipping",
            "the model processes input images at real-time frame rates on standard hardware",
            "our loss function balances localization accuracy and classification objectives",
            "the backbone network uses residual connections for deep feature extraction",
        ],
    },
    "natural_language_processing": {
        "titles": [
            "Transformer Models for Document Summarization",
            "Named Entity Recognition in Biomedical Text",
            "Sentiment Analysis with Contextual Embeddings",
            "Machine Translation for Low-Resource Languages",
            "Question Answering over Knowledge Graphs",
            "Text Classification with Pre-trained Language Models",
            "Dialogue Systems with Persona Consistency",
            "Relation Extraction from Scientific Literature",
            "Cross-Lingual Transfer for Multilingual NLP",
            "Aspect-Based Sentiment Analysis in Reviews",
        ],
        "phrases": [
            "we fine-tune a transformer model for abstractive text summarization",
            "our named entity recognition system identifies biomedical entities accurately",
            "the contextual embeddings capture nuanced word meaning in context",
            "we train a neural machine translation model for low-resource language pairs",
            "the system answers questions by traversing knowledge graph triples",
            "our classifier uses pre-trained language model representations effectively",
            "the dialogue agent maintains consistent persona across multi-turn conversations",
            "we extract semantic relations between entities from scientific papers",
            "cross-lingual transfer enables zero-shot text classification in new languages",
            "the model identifies aspect-specific sentiment in product review text",
            "we use subword tokenization to handle out-of-vocabulary words gracefully",
            "the encoder-decoder architecture generates fluent and coherent text outputs",
            "our approach combines syntactic and semantic features for dependency parsing",
            "the language model is pre-trained on large-scale multilingual text corpora",
            "we evaluate using BLEU, ROUGE, and F1 score evaluation metrics",
        ],
    },
}


def generate_abstract(domain_name, phrases):
    """Generate a single abstract from domain phrases, targeting 40-120 words."""
    selected = random.sample(phrases, random.randint(4, 7))
    # Capitalize first phrase and join with periods
    sentences = []
    for i, phrase in enumerate(selected):
        s = phrase[0].upper() + phrase[1:]
        if not s.endswith("."):
            s += "."
        sentences.append(s)
    abstract = " ".join(sentences)
    return abstract


def main():
    os.makedirs("/app/data", exist_ok=True)

    domain_names = list(DOMAINS.keys())
    abstracts = []
    idx = 0

    # Distribute ~33-34 abstracts per domain to reach 200
    per_domain = 200 // len(domain_names)  # 33
    remainder = 200 % len(domain_names)    # 2

    for di, domain_name in enumerate(domain_names):
        count = per_domain + (1 if di < remainder else 0)
        titles = DOMAINS[domain_name]["titles"]
        phrases = DOMAINS[domain_name]["phrases"]

        for j in range(count):
            title = titles[j % len(titles)]
            # Add variation to title for duplicates
            if j >= len(titles):
                title = f"{title}: Part {j // len(titles) + 1}"

            abstract_text = generate_abstract(domain_name, phrases)

            abstracts.append({
                "id": idx,
                "title": title,
                "abstract": abstract_text,
                "domain": domain_name,
            })
            idx += 1

    # Shuffle to mix domains
    random.shuffle(abstracts)
    # Re-assign sequential ids after shuffle
    for i, a in enumerate(abstracts):
        a["id"] = i

    with open("/app/data/abstracts.json", "w") as f:
        json.dump(abstracts, f, indent=2)

    print(f"Generated {len(abstracts)} abstracts across {len(domain_names)} domains")
    # Verify word counts
    for a in abstracts:
        wc = len(a["abstract"].split())
        assert 30 <= wc <= 150, f"Abstract {a['id']} has {wc} words"
    print("All abstracts pass word count validation.")


if __name__ == "__main__":
    main()
