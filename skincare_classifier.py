#!/usr/bin/env python3

import torch
from transformers import ViTImageProcessor, ViTForImageClassification
from PIL import Image
import json
from pathlib import Path
from typing import List, Dict, Union
import argparse

class SkincareClassifier:
    def __init__(self, model_name: str = '0xnu/skincare-detection'):
        self.processor = ViTImageProcessor.from_pretrained(model_name)
        self.model = ViTForImageClassification.from_pretrained(model_name)
        self.model.eval()
        self.id2label = self.model.config.id2label

    def classify(self, image_path: Union[str, Path], min_conf: float = 0.01) -> Dict:
        try:
            image = Image.open(image_path).convert('RGB')
            inputs = self.processor(images=image, return_tensors='pt')

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)[0]

            pred_id = outputs.logits.argmax().item()
            scores = {self.id2label[i]: float(probs[i]) for i in range(len(probs)) if probs[i] >= min_conf}

            return {
                'image': Path(image_path).name,
                'prediction': self.id2label[pred_id],
                'confidence': float(probs[pred_id]),
                'all_scores': dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
            }
        except Exception as e:
            return {'image': str(image_path), 'error': str(e)}

    def classify_batch(self, paths: List[Union[str, Path]], **kwargs) -> List[Dict]:
        return [self.classify(path, **kwargs) for path in paths]

    def classify_dir(self, dir_path: Union[str, Path], **kwargs) -> List[Dict]:
        extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        paths = [p for p in Path(dir_path).rglob('*') if p.suffix.lower() in extensions]
        return self.classify_batch(paths, **kwargs) if paths else []

    def print_results(self, results: Union[Dict, List[Dict]]):
        if isinstance(results, dict):
            results = [results]

        for r in results:
            if 'error' in r:
                print(f"❌ {r['image']}: {r['error']}")
                continue

            print(f"📸 {r['image']}")
            print(f"🎯 {r['prediction'].upper()}: {r['confidence']:.1%}")

            for cls, conf in r['all_scores'].items():
                bar = '█' * int(conf * 20)
                print(f"   {cls:>8}: {conf:.1%} {bar}")
            print('-' * 30)


def main():
    parser = argparse.ArgumentParser(description='Skincare Image Classification')
    parser.add_argument('input', help='Image file or directory')
    parser.add_argument('--model', default='0xnu/skincare-detection')
    parser.add_argument('--output', help='JSON output file')
    parser.add_argument('--min-conf', type=float, default=0.01)
    args = parser.parse_args()

    classifier = SkincareClassifier(args.model)
    input_path = Path(args.input)

    if input_path.is_file():
        results = classifier.classify(input_path, args.min_conf)
    elif input_path.is_dir():
        results = classifier.classify_dir(input_path, min_conf=args.min_conf)
    else:
        return print(f"❌ Invalid path: {input_path}")

    classifier.print_results(results)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        classifier = SkincareClassifier()
        if Path('joe.jpeg').exists():
            classifier.print_results(classifier.classify('joe.jpeg'))
        else:
            print('Usage: python skincare_classifier.py <image_path>')
    else:
        main()
