#!/usr/bin/env python3
"""
Knowledge Base Processing for Property-Based Method

Processes trained model predictions to:
- Compute effectiveness metrics for each of 31 properties
- Implement weighted voting ensemble
- Generate architecture-level decisions with confidence scores

Input: Folder with training outputs (train_pred.json, test_pred.json, etc.)
Output: arch_preds.json, arch_decisions.json, similar.json (empty stub)
"""

import os
import json
import numpy as np
from datetime import datetime
from sklearn.metrics import (
    confusion_matrix, precision_recall_fscore_support, 
    accuracy_score, matthews_corrcoef, f1_score, 
    cohen_kappa_score, roc_auc_score
)


def calc_specificity(tn, fp):
    """Calculate specificity, returns 0.0 if zero denominator"""
    result = 0.0
    if tn + fp > 0:
        result = tn / (tn + fp)
    return result


def get_num_classes(preds):
    """Get number of unique classes in predictions"""
    max_class = max(preds)
    min_class = min(preds)
    return max_class - min_class + 1


def analyze_results(labels, predictions):
    """Compute and print classification metrics"""
    all_labels = []
    all_labels.extend(labels)
    all_labels.extend(predictions)
    num_classes = get_num_classes(all_labels)
    class_counts = [0.0] * num_classes
    class_correct = [0.0] * num_classes
    conf_matrix = []
    class_header = [None]
    for i in range(num_classes):
        class_header.append(i)
        conf_matrix.append([0] * num_classes)
    for pred_ix, p in enumerate(predictions):
        if labels[pred_ix] == p:
            class_correct[labels[pred_ix]] += 1.0
        class_counts[labels[pred_ix]] += 1.0
        conf_matrix[labels[pred_ix]][p] += 1
    
    # Output results
    print("\n\tAccuracy per class:\n\t| class | accuracy |\n\t| :---: | :---: |")
    for i in range(num_classes):
        accuracy_val = 0.0
        if class_counts[i] != 0:
            accuracy_val = class_correct[i] / class_counts[i]
        print("\t|", i, " | ", round(accuracy_val, 3), " |")
    print("\n\tconfusion matrix (columns=predictions, rows=as labeled)")
    conf_matrix_string = "\t" + str(class_header) + "\n\t"
    for row_ix, row in enumerate(conf_matrix):
        conf_matrix_string += str(row_ix)
        for n in row:
            conf_matrix_string += ", " + str(n)
        conf_matrix_string += "\n\t"
    print(conf_matrix_string)
    cm = confusion_matrix(labels, predictions)
    print("\tCM:")
    for row in cm:
        print("\t", row)
    if num_classes > 1:
        tn, fp, fn, tp = cm.ravel()
        print("\tTN:", tn, ", TP:", tp, ", FN:", fn, ", FP", fp)
        print("\tTPR:", round(tp / (tp + fn), 3), ", TNR: ", round(tn / (tn + fp), 3))


def process_kb(input_folder, output_folder):
    """
    Process knowledge base from trained SVM predictions
    
    Args:
        input_folder: Folder containing training outputs (train_pred.json, etc.)
        output_folder: Output folder for processed KB
        
    Returns:
        dict: Processing results including predictions and decisions
    """
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    print("="*80)
    print("Knowledge Base Processing Started")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    print(f"Input folder:  {input_folder}")
    print(f"Output folder: {output_folder}")
    print("")
    
    # Load KB data
    print("Loading prediction data...")
    with open(os.path.join(input_folder, "train_pred.json")) as infile:
        train_pred = json.load(infile)
    
    with open(os.path.join(input_folder, "train_proba.json")) as infile:
        train_proba = json.load(infile)
        
    with open(os.path.join(input_folder, "train_labels.json")) as infile:
        train_labels = json.load(infile)
    
    with open(os.path.join(input_folder, "test_pred.json")) as infile:
        test_pred = json.load(infile)
    
    with open(os.path.join(input_folder, "test_proba.json")) as infile:
        test_proba = json.load(infile)
    
    with open(os.path.join(input_folder, "test_labels.json")) as infile:
        test_labels = json.load(infile)
    
    with open(os.path.join(input_folder, "properties.json")) as infile:
        properties = json.load(infile)
    
    with open(os.path.join(input_folder, "scaled_training_data.json")) as infile:
        base_training = json.load(infile)
    
    with open(os.path.join(input_folder, "scaled_test_data.json")) as infile:
        base_test = json.load(infile)
    
    with open(os.path.join(input_folder, "test_data.json")) as infile:
        test_data = json.load(infile)
    
    min_label = min(train_labels)
    max_label = max(train_labels)
    
    print(f"Loaded {len(properties)} properties")
    print(f"Training samples: {len(train_labels)}")
    print(f"Test samples: {len(test_labels)}")
    print(f"Label range: {min_label} to {max_label}")
    print("")
    
    # Compute effectiveness of each property
    print("Computing property effectiveness metrics...")
    explainability = []  # How explainable each property is (fewer features = more explainable)
    effectiveness = []   # Effectiveness metrics for each property
    
    for ix, property in enumerate(properties):
        expl = 1.0 - (len(property) - 1) * .25
        explainability.append(expl)
        
        train_cm = confusion_matrix(train_labels, train_pred[ix])
        test_cm = confusion_matrix(test_labels, test_pred[ix])
        tn, fp, fn, tp = train_cm.ravel()
        precision, recall, fscore, support = precision_recall_fscore_support(train_labels, train_pred[ix])
        accuracy = accuracy_score(train_labels, train_pred[ix])
        specificity = calc_specificity(tn, fp)
        epars = precision * accuracy * recall * specificity
        cohen_kappa = cohen_kappa_score(train_labels, train_pred[ix])
        mcc = matthews_corrcoef(train_labels, train_pred[ix])
        auc = roc_auc_score(train_labels, train_pred[ix])
        f1 = f1_score(train_labels, train_pred[ix])
        
        eff = {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "accuracy": accuracy,
            "specificity": specificity,
            "epars": epars.tolist(),
            "fscore": fscore.tolist(),
            "f1": f1,
            "cohen_kappa": cohen_kappa,
            "mcc": mcc,
            "auc": auc,
            "tpr": tp / (tp + fn),
            "cm": train_cm.tolist()
        }
        
        effectiveness.append(eff)
        print(f"  Property {ix:2d}: {property} | Expl: {expl:.2f} | F1: {f1:.4f} | TPR: {eff['tpr']:.4f}")
    
    print("")
    
    # Generate architecture predictions using weighted voting
    print("Generating ensemble predictions via weighted voting...")
    arch_preds = []
    arch_decisions = []
    
    for i, label in enumerate(test_labels):
        votes = []
        tally = [0.0, 0.0]
        expl_tally = [0.0, 0.0]
        
        for j, prop in enumerate(properties):
            pred = test_pred[j][i]
            proba = test_proba[j][i][pred]
            epars = effectiveness[j]["epars"][0] * effectiveness[j]["epars"][1]
            tpr = effectiveness[j]["tpr"]
            eff = epars
            tally[pred] += eff
            expl = explainability[j]
            expl_tally[pred] += eff * expl
            
            vote = {
                "property": prop,
                "prediction": pred,
                "probability": proba,
                "effectiveness": eff,
                "explainability": expl,
                "tpr": tpr
            }
            votes.append(vote)
        
        max_val = max(tally)
        weight = tally[0] + tally[1]
        winner = tally.index(max_val)
        arch_preds.append(winner)
        
        arch_decisions.append({
            "index": i,
            "label": label,
            "winner": winner,
            "confidence": tally[winner] / weight if weight > 0 else 0.0,
            "vote_tally": tally,
            "explainability_tally": expl_tally,
            "votes": votes
        })
    
    print(f"Generated {len(arch_preds)} ensemble predictions")
    print("")
    
    # Analyze results
    print("="*80)
    print("Ensemble Results:")
    print("="*80)
    analyze_results(test_labels, arch_preds)
    print("")
    
    # Save outputs
    print("Saving outputs...")
    
    # Write system predictions
    with open(os.path.join(output_folder, "arch_preds.json"), 'w') as outfile:
        json.dump(arch_preds, outfile)
    print(f"  Saved arch_preds.json")
    
    # Write system decisions
    with open(os.path.join(output_folder, "arch_decisions.json"), 'w') as outfile:
        json.dump(arch_decisions, outfile, indent=4)
    print(f"  Saved arch_decisions.json")
    
    # Write empty similar.json structure (required by Phase 5 - explanation generation)
    # NOTE: Case-based similarity belongs to Method 2, not Method 1
    # This creates an empty structure so Phase 5 can run without errors
    similar_training = []
    with open(os.path.join(output_folder, "similar.json"), 'w') as outfile:
        json.dump(similar_training, outfile, indent=2)
    print(f"  Saved similar.json (empty stub for Method 2 compatibility)")
    
    print("")
    print("="*80)
    print("Knowledge Base Processing Complete!")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*80)
    
    return {
        'predictions': arch_preds,
        'decisions': arch_decisions,
        'effectiveness': effectiveness,
        'explainability': explainability
    }
