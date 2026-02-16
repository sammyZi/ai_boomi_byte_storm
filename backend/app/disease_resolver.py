"""Intelligent Disease Resolution System - "Just Enter Disease Name" Architecture

This module implements a 5-layer disease resolution system:
Layer 1: Input Normalization - Typo correction, synonym expansion, abbreviation handling
Layer 2: Multi-Ontology Lookup - EFO, Disease Ontology, MeSH cross-referencing
Layer 3: Hierarchical Expansion - Walk up ontology tree to find ancestor with targets
Layer 4: NLP Semantic Matching - Vectorize input, cosine similarity matching
Layer 5: Smart Fallbacks - Symptom detection, ambiguity handling, category browsing

Scoring: 0.4×exact_match + 0.3×semantic_similarity + 0.2×target_count + 0.1×ontology_trust
"""

import asyncio
import re
import math
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
from functools import lru_cache
import time

from config.settings import settings


class MatchType(str, Enum):
    """Types of disease matches"""
    EXACT = "exact"              # Direct name match
    SYNONYM = "synonym"          # Known synonym match
    TYPO_CORRECTED = "typo_corrected"  # Levenshtein-corrected
    SEMANTIC = "semantic"        # NLP similarity match
    HIERARCHICAL = "hierarchical"  # Parent/ancestor match
    FALLBACK = "fallback"        # Category-based fallback
    PARTIAL = "partial"          # Partial word match


class ConfidenceLevel(str, Enum):
    """Confidence levels for UI display"""
    HIGH = "high"       # Green - confident match
    MEDIUM = "medium"   # Yellow - needs confirmation
    LOW = "low"         # Red - uncertain, suggestions offered


@dataclass
class DiseaseMatch:
    """A resolved disease match with metadata"""
    disease_id: str              # EFO ID or ontology ID
    disease_name: str            # Canonical disease name
    match_type: MatchType        # How the match was found
    confidence: float            # 0-1 confidence score
    confidence_level: ConfidenceLevel  # For UI display
    target_count: int = 0        # Number of known targets
    synonyms: List[str] = field(default_factory=list)
    description: str = ""        # Disease description
    ontology_source: str = "EFO" # Source ontology
    original_query: str = ""     # What user typed
    correction_applied: str = "" # If typo was corrected
    parent_diseases: List[str] = field(default_factory=list)


@dataclass
class SuggestionResponse:
    """Response for disease suggestions endpoint"""
    query: str
    suggestions: List[DiseaseMatch]
    confidence_level: ConfidenceLevel
    message: str  # "Found exact match" / "Did you mean..." / "No matches found"
    processing_time_ms: int


# ==================== LAYER 1: Input Normalization ====================

class InputNormalizer:
    """Layer 1: Normalize and correct user input"""
    
    # Common medical abbreviations and their expansions
    ABBREVIATIONS: Dict[str, str] = {
        "ad": "Alzheimer's disease",
        "pd": "Parkinson's disease",
        "t2d": "Type 2 diabetes",
        "t1d": "Type 1 diabetes",
        "dm": "diabetes mellitus",
        "dm2": "Type 2 diabetes",
        "dm1": "Type 1 diabetes",
        "ra": "rheumatoid arthritis",
        "ms": "multiple sclerosis",
        "als": "amyotrophic lateral sclerosis",
        "copd": "chronic obstructive pulmonary disease",
        "cad": "coronary artery disease",
        "chf": "congestive heart failure",
        "hf": "heart failure",
        "ckd": "chronic kidney disease",
        "ibd": "inflammatory bowel disease",
        "uc": "ulcerative colitis",
        "cd": "Crohn's disease",
        "htn": "hypertension",
        "mi": "myocardial infarction",
        "cva": "cerebrovascular accident",
        "dvt": "deep vein thrombosis",
        "pe": "pulmonary embolism",
        "ards": "acute respiratory distress syndrome",
        "sle": "systemic lupus erythematosus",
        "lupus": "systemic lupus erythematosus",
        "hiv": "human immunodeficiency virus infection",
        "aids": "acquired immunodeficiency syndrome",
        "nash": "non-alcoholic steatohepatitis",
        "nafld": "non-alcoholic fatty liver disease",
        "gerd": "gastroesophageal reflux disease",
        "bph": "benign prostatic hyperplasia",
        "ptsd": "post-traumatic stress disorder",
        "ocd": "obsessive-compulsive disorder",
        "adhd": "attention deficit hyperactivity disorder",
        "aml": "acute myeloid leukemia",
        "cml": "chronic myeloid leukemia",
        "all": "acute lymphoblastic leukemia",
        "cll": "chronic lymphocytic leukemia",
        "nsclc": "non-small cell lung cancer",
        "sclc": "small cell lung cancer",
        "hcc": "hepatocellular carcinoma",
        "rcc": "renal cell carcinoma",
        "crc": "colorectal cancer",
        "glioma": "brain glioma",
        "gbm": "glioblastoma multiforme",
        "mdd": "major depressive disorder",
        "gad": "generalized anxiety disorder",
        "cf": "cystic fibrosis",
        "scd": "sickle cell disease",
        "thalassemia": "beta thalassemia",
    }
    
    # Common typos and corrections for disease names
    COMMON_TYPOS: Dict[str, str] = {
        "alzeimer": "alzheimer",
        "alzheimers": "alzheimer's",
        "alzheimer": "alzheimer's",
        "parkinsons": "parkinson's",
        "parkinson": "parkinson's",
        "diabetis": "diabetes",
        "diabeties": "diabetes",
        "diabet": "diabetes",
        "rheumatoid arthiritis": "rheumatoid arthritis",
        "arthritus": "arthritis",
        "arthiritis": "arthritis",
        "cancr": "cancer",
        "cnacer": "cancer",
        "lukemia": "leukemia",
        "leukimia": "leukemia",
        "melonoma": "melanoma",
        "melanomia": "melanoma",
        "asthama": "asthma",
        "astma": "asthma",
        "dipression": "depression",
        "depresion": "depression",
        "anxeity": "anxiety",
        "anxity": "anxiety",
        "schizophrnia": "schizophrenia",
        "schizophernia": "schizophrenia",
        "hypertention": "hypertension",
        "hipertension": "hypertension",
        "hepatitus": "hepatitis",
        "hepatits": "hepatitis",
        "fibrosis": "fibrosis",
        "fibrous": "fibrosis",
        "sclerosis": "sclerosis",
        "sklerosis": "sclerosis",
        "cardiomiopathy": "cardiomyopathy",
        "cardiomyapathy": "cardiomyopathy",
        "neuropathy": "neuropathy",
        "nueropath": "neuropathy",
        "inflamation": "inflammation",
        "inflamatory": "inflammatory",
        "inflammtory": "inflammatory",
        "autoimmue": "autoimmune",
        "autoimune": "autoimmune",
        "chrohns": "crohn's",
        "crohns": "crohn's",
        "ulceritive": "ulcerative",
        "colitus": "colitis",
    }
    
    @classmethod
    def normalize(cls, query: str) -> Tuple[str, Optional[str]]:
        """
        Normalize user input.
        
        Returns:
            Tuple of (normalized_query, correction_applied or None)
        """
        if not query:
            return "", None
        
        # Basic cleanup
        normalized = query.strip().lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Check for abbreviation expansion
        if normalized in cls.ABBREVIATIONS:
            return cls.ABBREVIATIONS[normalized], f"Expanded abbreviation: {query.upper()}"
        
        # Check for known typos
        correction_applied = None
        words = normalized.split()
        corrected_words = []
        
        for word in words:
            if word in cls.COMMON_TYPOS:
                corrected_words.append(cls.COMMON_TYPOS[word])
                correction_applied = f"Corrected: {word} -> {cls.COMMON_TYPOS[word]}"
            else:
                corrected_words.append(word)
        
        normalized = ' '.join(corrected_words)
        
        # Levenshtein-based correction for unknown words
        if not correction_applied:
            for typo, correct in cls.COMMON_TYPOS.items():
                if cls._levenshtein_distance(normalized, typo) <= 2:
                    normalized = correct
                    correction_applied = f"Corrected: {query} -> {correct}"
                    break
        
        return normalized, correction_applied
    
    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return InputNormalizer._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def suggest_corrections(cls, query: str, max_suggestions: int = 5) -> List[Tuple[str, int]]:
        """
        Suggest possible corrections based on Levenshtein distance.
        
        Returns:
            List of (suggestion, distance) tuples sorted by distance
        """
        query_lower = query.lower().strip()
        suggestions = []
        
        # Check abbreviations
        for abbrev, expansion in cls.ABBREVIATIONS.items():
            dist = cls._levenshtein_distance(query_lower, abbrev)
            if dist <= 2:
                suggestions.append((expansion, dist))
        
        # Check common disease terms
        all_terms = list(cls.ABBREVIATIONS.values()) + list(cls.COMMON_TYPOS.values())
        unique_terms = list(set(all_terms))
        
        for term in unique_terms:
            dist = cls._levenshtein_distance(query_lower, term.lower())
            if dist <= 3:
                suggestions.append((term, dist))
        
        # Sort by distance and deduplicate
        suggestions = sorted(set(suggestions), key=lambda x: x[1])
        return suggestions[:max_suggestions]


# ==================== LAYER 2: Multi-Ontology Lookup ====================

class OntologyLookup:
    """Layer 2: Query multiple disease ontologies"""
    
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.open_targets_url = settings.open_targets_api_url
    
    async def search_efo(self, query: str, max_results: int = 10) -> List[DiseaseMatch]:
        """
        Search EFO (Experimental Factor Ontology) via Open Targets.
        EFO has ~20,000 disease terms.
        """
        graphql_query = """
        query SearchDisease($queryString: String!, $size: Int!) {
          search(queryString: $queryString, entityNames: ["disease"], page: {index: 0, size: $size}) {
            total
            hits {
              id
              name
              description
              entity
              score
            }
          }
        }
        """
        
        variables = {"queryString": query, "size": max_results}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.open_targets_url}/graphql",
                    json={"query": graphql_query, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            # Log error but don't fail - return empty results
            print(f"EFO search error: {e}")
            return []
        
        hits = data.get("data", {}).get("search", {}).get("hits", [])
        matches = []
        
        for hit in hits:
            # Determine match type and confidence
            hit_name = hit.get("name", "").lower()
            query_lower = query.lower()
            
            if hit_name == query_lower:
                match_type = MatchType.EXACT
                confidence = 0.95
            elif query_lower in hit_name or hit_name in query_lower:
                match_type = MatchType.PARTIAL
                confidence = 0.80
            else:
                match_type = MatchType.SEMANTIC
                # Use search score from Open Targets
                confidence = min(0.7, hit.get("score", 0.5))
            
            # Determine confidence level for UI
            if confidence >= 0.85:
                confidence_level = ConfidenceLevel.HIGH
            elif confidence >= 0.6:
                confidence_level = ConfidenceLevel.MEDIUM
            else:
                confidence_level = ConfidenceLevel.LOW
            
            match = DiseaseMatch(
                disease_id=hit.get("id", ""),
                disease_name=hit.get("name", ""),
                match_type=match_type,
                confidence=confidence,
                confidence_level=confidence_level,
                description=hit.get("description", ""),
                ontology_source="EFO",
                original_query=query
            )
            matches.append(match)
        
        return matches
    
    async def get_disease_details(self, disease_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed disease information including target count.
        """
        graphql_query = """
        query DiseaseInfo($efoId: String!) {
          disease(efoId: $efoId) {
            id
            name
            description
            synonyms {
              terms
            }
            parents {
              id
              name
            }
            associatedTargets {
              count
            }
          }
        }
        """
        
        variables = {"efoId": disease_id}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.open_targets_url}/graphql",
                    json={"query": graphql_query, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            print(f"Disease details error: {e}")
            return None
        
        disease_data = data.get("data", {}).get("disease", {})
        if not disease_data:
            return None
        
        # Extract synonyms - can be a list or a dict with "terms" key
        synonyms = []
        synonym_obj = disease_data.get("synonyms", [])
        if synonym_obj:
            if isinstance(synonym_obj, list):
                # It's a list of synonym objects or strings
                for item in synonym_obj:
                    if isinstance(item, str):
                        synonyms.append(item)
                    elif isinstance(item, dict) and "terms" in item:
                        synonyms.extend(item.get("terms", []))
            elif isinstance(synonym_obj, dict):
                # It's a dict with "terms" key
                synonyms = synonym_obj.get("terms", [])
        
        # Extract parents
        parents = [p.get("name", "") for p in disease_data.get("parents", [])]
        
        # Get target count
        target_count = disease_data.get("associatedTargets", {}).get("count", 0)
        
        return {
            "disease_id": disease_data.get("id", disease_id),
            "disease_name": disease_data.get("name", ""),
            "description": disease_data.get("description", ""),
            "synonyms": synonyms,
            "parent_diseases": parents,
            "target_count": target_count
        }


# ==================== LAYER 3: Hierarchical Expansion ====================

class HierarchicalExpander:
    """Layer 3: Walk up ontology tree to find diseases with targets"""
    
    def __init__(self, ontology_lookup: OntologyLookup):
        self.ontology = ontology_lookup
        self.min_target_threshold = 5  # Minimum targets to consider a disease useful
    
    async def find_ancestor_with_targets(
        self, 
        disease_id: str, 
        max_depth: int = 3
    ) -> Optional[DiseaseMatch]:
        """
        Walk up the ontology tree to find an ancestor disease with sufficient targets.
        
        This helps when user searches for a very specific disease with no direct targets,
        by suggesting a broader parent disease.
        """
        visited = set()
        current_id = disease_id
        depth = 0
        
        while depth < max_depth and current_id and current_id not in visited:
            visited.add(current_id)
            
            details = await self.ontology.get_disease_details(current_id)
            if not details:
                break
            
            # Check if this disease has enough targets
            if details.get("target_count", 0) >= self.min_target_threshold:
                return DiseaseMatch(
                    disease_id=details["disease_id"],
                    disease_name=details["disease_name"],
                    match_type=MatchType.HIERARCHICAL,
                    confidence=0.7 - (depth * 0.1),  # Decrease confidence for ancestors
                    confidence_level=ConfidenceLevel.MEDIUM,
                    target_count=details["target_count"],
                    synonyms=details.get("synonyms", []),
                    description=details.get("description", ""),
                    parent_diseases=details.get("parent_diseases", []),
                    original_query=disease_id
                )
            
            # Move to parent
            parents = details.get("parent_diseases", [])
            if parents:
                # Get parent ID by searching for it
                parent_matches = await self.ontology.search_efo(parents[0], max_results=1)
                if parent_matches:
                    current_id = parent_matches[0].disease_id
                else:
                    break
            else:
                break
            
            depth += 1
        
        return None


# ==================== LAYER 4: NLP Semantic Matching ====================

class SemanticMatcher:
    """Layer 4: NLP-based semantic matching for disease names"""
    
    # Common disease-related terms for TF-IDF-like matching
    DISEASE_VOCABULARY: List[str] = [
        "disease", "disorder", "syndrome", "condition", "infection",
        "cancer", "carcinoma", "tumor", "neoplasm", "malignancy",
        "deficiency", "failure", "dysfunction", "impairment",
        "inflammation", "inflammatory", "autoimmune", "chronic", "acute",
        "genetic", "hereditary", "congenital", "degenerative", "progressive",
        "neurological", "cardiovascular", "respiratory", "metabolic",
        "psychiatric", "mental", "cognitive", "developmental",
        "primary", "secondary", "idiopathic", "familial",
    ]
    
    @classmethod
    def calculate_similarity(cls, query: str, target: str) -> float:
        """
        Calculate cosine similarity between query and target disease name.
        Uses a simple bag-of-words approach with medical term weighting.
        """
        query_words = set(cls._tokenize(query))
        target_words = set(cls._tokenize(target))
        
        if not query_words or not target_words:
            return 0.0
        
        # Calculate intersection
        intersection = query_words & target_words
        
        if not intersection:
            return 0.0
        
        # Weight medical terms higher
        weighted_intersection = 0.0
        for word in intersection:
            if word in cls.DISEASE_VOCABULARY:
                weighted_intersection += 1.5
            else:
                weighted_intersection += 1.0
        
        # Cosine similarity approximation
        magnitude1 = math.sqrt(len(query_words))
        magnitude2 = math.sqrt(len(target_words))
        
        similarity = weighted_intersection / (magnitude1 * magnitude2)
        
        # Normalize to 0-1 range
        return min(1.0, similarity)
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize and clean text"""
        # Remove special characters
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split into words
        words = cleaned.split()
        # Remove very short words
        return [w for w in words if len(w) > 2]
    
    @classmethod
    def find_best_semantic_match(
        cls, 
        query: str, 
        candidates: List[DiseaseMatch],
        threshold: float = 0.5
    ) -> List[DiseaseMatch]:
        """
        Rank candidates by semantic similarity to query.
        """
        scored_matches = []
        
        for candidate in candidates:
            # Calculate similarity
            similarity = cls.calculate_similarity(query, candidate.disease_name)
            
            # Also check synonyms
            max_synonym_sim = 0.0
            for synonym in candidate.synonyms:
                syn_sim = cls.calculate_similarity(query, synonym)
                max_synonym_sim = max(max_synonym_sim, syn_sim)
            
            # Use the higher of name or synonym similarity
            final_similarity = max(similarity, max_synonym_sim)
            
            if final_similarity >= threshold:
                # Update confidence based on semantic matching
                candidate.confidence = 0.4 * candidate.confidence + 0.6 * final_similarity
                candidate.match_type = MatchType.SEMANTIC
                
                # Update confidence level
                if candidate.confidence >= 0.75:
                    candidate.confidence_level = ConfidenceLevel.HIGH
                elif candidate.confidence >= 0.5:
                    candidate.confidence_level = ConfidenceLevel.MEDIUM
                else:
                    candidate.confidence_level = ConfidenceLevel.LOW
                
                scored_matches.append(candidate)
        
        # Sort by confidence
        scored_matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return scored_matches


# ==================== LAYER 5: Smart Fallbacks ====================

class SmartFallback:
    """Layer 5: Fallback strategies when no direct match found"""
    
    # Symptom to disease category mappings
    SYMPTOM_MAPPINGS: Dict[str, List[str]] = {
        "memory loss": ["Alzheimer's disease", "dementia"],
        "tremor": ["Parkinson's disease", "essential tremor"],
        "shaking": ["Parkinson's disease", "essential tremor"],
        "high blood sugar": ["Type 2 diabetes", "diabetes mellitus"],
        "weight gain": ["obesity", "hypothyroidism"],
        "weight loss": ["hyperthyroidism", "cancer"],
        "fatigue": ["chronic fatigue syndrome", "depression", "anemia"],
        "chest pain": ["coronary artery disease", "angina"],
        "shortness of breath": ["COPD", "heart failure", "asthma"],
        "joint pain": ["rheumatoid arthritis", "osteoarthritis"],
        "skin rash": ["psoriasis", "eczema", "lupus"],
        "headache": ["migraine", "tension headache"],
        "seizures": ["epilepsy"],
        "vision loss": ["macular degeneration", "glaucoma"],
        "hearing loss": ["presbycusis", "otosclerosis"],
        "muscle weakness": ["muscular dystrophy", "myasthenia gravis"],
        "numbness": ["multiple sclerosis", "neuropathy"],
        "confusion": ["dementia", "delirium"],
    }
    
    # Disease categories for browsing
    DISEASE_CATEGORIES: Dict[str, List[str]] = {
        "neurological": [
            "Alzheimer's disease", "Parkinson's disease", "Multiple sclerosis",
            "Epilepsy", "ALS", "Huntington's disease"
        ],
        "cardiovascular": [
            "Coronary artery disease", "Heart failure", "Hypertension",
            "Atrial fibrillation", "Cardiomyopathy"
        ],
        "cancer": [
            "Breast cancer", "Lung cancer", "Colorectal cancer",
            "Prostate cancer", "Leukemia", "Lymphoma"
        ],
        "autoimmune": [
            "Rheumatoid arthritis", "Lupus", "Multiple sclerosis",
            "Crohn's disease", "Ulcerative colitis"
        ],
        "metabolic": [
            "Type 2 diabetes", "Type 1 diabetes", "Obesity",
            "Hypothyroidism", "Hyperthyroidism"
        ],
        "respiratory": [
            "Asthma", "COPD", "Cystic fibrosis",
            "Pulmonary fibrosis", "Pulmonary hypertension"
        ],
        "psychiatric": [
            "Depression", "Anxiety", "Schizophrenia",
            "Bipolar disorder", "PTSD"
        ],
        "infectious": [
            "HIV/AIDS", "Hepatitis B", "Hepatitis C",
            "Tuberculosis", "Malaria"
        ]
    }
    
    @classmethod
    def detect_symptom(cls, query: str) -> Optional[List[str]]:
        """
        Check if query describes symptoms rather than a disease.
        Returns suggested diseases based on symptoms.
        """
        query_lower = query.lower()
        
        for symptom, diseases in cls.SYMPTOM_MAPPINGS.items():
            if symptom in query_lower:
                return diseases
        
        return None
    
    @classmethod
    def suggest_category_diseases(cls, query: str) -> Optional[Tuple[str, List[str]]]:
        """
        If query mentions a disease category, return diseases in that category.
        """
        query_lower = query.lower()
        
        for category, diseases in cls.DISEASE_CATEGORIES.items():
            if category in query_lower:
                return (category, diseases)
        
        return None
    
    @classmethod
    def get_fallback_suggestions(
        cls, 
        query: str, 
        max_suggestions: int = 5
    ) -> List[DiseaseMatch]:
        """
        Generate fallback suggestions when no direct match found.
        """
        suggestions = []
        
        # Check for symptom-based suggestions
        symptom_diseases = cls.detect_symptom(query)
        if symptom_diseases:
            for disease in symptom_diseases[:max_suggestions]:
                suggestions.append(DiseaseMatch(
                    disease_id="",  # Will be resolved later
                    disease_name=disease,
                    match_type=MatchType.FALLBACK,
                    confidence=0.5,
                    confidence_level=ConfidenceLevel.MEDIUM,
                    original_query=query,
                    correction_applied=f"Based on symptom: {query}"
                ))
        
        # Check for category-based suggestions
        category_result = cls.suggest_category_diseases(query)
        if category_result:
            category, diseases = category_result
            for disease in diseases[:max_suggestions - len(suggestions)]:
                if not any(s.disease_name == disease for s in suggestions):
                    suggestions.append(DiseaseMatch(
                        disease_id="",
                        disease_name=disease,
                        match_type=MatchType.FALLBACK,
                        confidence=0.4,
                        confidence_level=ConfidenceLevel.LOW,
                        original_query=query,
                        correction_applied=f"Category: {category}"
                    ))
        
        return suggestions[:max_suggestions]


# ==================== MAIN RESOLVER ====================

class DiseaseResolver:
    """
    Main disease resolution orchestrator.
    Combines all 5 layers to provide intelligent disease resolution.
    """
    
    def __init__(self):
        self.normalizer = InputNormalizer()
        self.ontology = OntologyLookup()
        self.hierarchical = HierarchicalExpander(self.ontology)
        self.semantic = SemanticMatcher()
        self.fallback = SmartFallback()
        
        # Simple in-memory cache for hot diseases
        self._cache: Dict[str, Tuple[List[DiseaseMatch], float]] = {}
        self._cache_ttl = 3600  # 1 hour
        
        # Optional Redis cache adapter (set via configure_redis_cache)
        self.redis_cache: Optional[Any] = None
    
    async def resolve(
        self, 
        query: str, 
        max_suggestions: int = 10
    ) -> SuggestionResponse:
        """
        Resolve a disease query through all 5 layers.
        
        Args:
            query: User's disease search query
            max_suggestions: Maximum suggestions to return
        
        Returns:
            SuggestionResponse with ranked suggestions
        """
        start_time = time.time()
        
        if not query or len(query.strip()) < 2:
            return SuggestionResponse(
                query=query,
                suggestions=[],
                confidence_level=ConfidenceLevel.LOW,
                message="Please enter at least 2 characters",
                processing_time_ms=0
            )
        
        # Check cache (Redis first, then in-memory)
        cache_key = query.lower().strip()
        
        # Try Redis cache first
        if self.redis_cache:
            try:
                redis_result = await self.redis_cache.get(cache_key)
                if redis_result:
                    return SuggestionResponse(
                        query=query,
                        suggestions=redis_result,
                        confidence_level=redis_result[0].confidence_level if redis_result else ConfidenceLevel.LOW,
                        message=self._get_message(redis_result),
                        processing_time_ms=int((time.time() - start_time) * 1000)
                    )
            except Exception as e:
                print(f"Redis cache error: {e}")
        
        # Check in-memory cache
        if cache_key in self._cache:
            cached_result, cache_time = self._cache[cache_key]
            if time.time() - cache_time < self._cache_ttl:
                return SuggestionResponse(
                    query=query,
                    suggestions=cached_result,
                    confidence_level=cached_result[0].confidence_level if cached_result else ConfidenceLevel.LOW,
                    message=self._get_message(cached_result),
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
        
        # Layer 1: Normalize input
        normalized_query, correction = self.normalizer.normalize(query)
        
        # Layer 2: Multi-ontology lookup
        efo_matches = await self.ontology.search_efo(normalized_query, max_results=max_suggestions)
        
        # Enrich matches with details (target counts, synonyms)
        enriched_matches = []
        for match in efo_matches[:5]:  # Limit to top 5 for detail enrichment
            details = await self.ontology.get_disease_details(match.disease_id)
            if details:
                match.target_count = details.get("target_count", 0)
                match.synonyms = details.get("synonyms", [])
                match.parent_diseases = details.get("parent_diseases", [])
                if correction:
                    match.correction_applied = correction
                enriched_matches.append(match)
            else:
                enriched_matches.append(match)
        
        # Add remaining matches without enrichment
        enriched_matches.extend(efo_matches[5:])
        
        # Layer 3: Hierarchical expansion for top match if no targets
        if enriched_matches and enriched_matches[0].target_count == 0:
            ancestor = await self.hierarchical.find_ancestor_with_targets(
                enriched_matches[0].disease_id
            )
            if ancestor:
                # Add ancestor as a suggestion
                ancestor.correction_applied = f"Broader: {enriched_matches[0].disease_name}"
                enriched_matches.insert(1, ancestor)
        
        # Layer 4: Semantic matching to rerank
        if len(enriched_matches) > 1:
            enriched_matches = self.semantic.find_best_semantic_match(
                query, enriched_matches, threshold=0.3
            ) or enriched_matches
        
        # Layer 5: Fallback if no good matches
        if not enriched_matches or enriched_matches[0].confidence < 0.5:
            # Try typo correction suggestions
            typo_suggestions = self.normalizer.suggest_corrections(query)
            for correction_text, distance in typo_suggestions:
                if distance <= 2:
                    correction_matches = await self.ontology.search_efo(
                        correction_text, max_results=3
                    )
                    for match in correction_matches:
                        match.correction_applied = f"Did you mean: {correction_text}?"
                        match.match_type = MatchType.TYPO_CORRECTED
                        match.confidence = max(0.6 - (distance * 0.1), 0.4)
                        match.confidence_level = ConfidenceLevel.MEDIUM
                        enriched_matches.append(match)
            
            # Fallback suggestions
            fallback_suggestions = self.fallback.get_fallback_suggestions(query)
            for suggestion in fallback_suggestions:
                # Try to resolve the fallback disease name
                fallback_matches = await self.ontology.search_efo(
                    suggestion.disease_name, max_results=1
                )
                if fallback_matches:
                    fallback_match = fallback_matches[0]
                    fallback_match.correction_applied = suggestion.correction_applied
                    fallback_match.match_type = MatchType.FALLBACK
                    fallback_match.confidence = 0.4
                    fallback_match.confidence_level = ConfidenceLevel.LOW
                    enriched_matches.append(fallback_match)
        
        # Deduplicate by disease_id
        seen_ids = set()
        unique_matches = []
        for match in enriched_matches:
            if match.disease_id not in seen_ids:
                seen_ids.add(match.disease_id)
                unique_matches.append(match)
        
        # Final ranking by composite score
        final_matches = self._rank_by_composite_score(unique_matches)[:max_suggestions]
        
        # Cache result (both in-memory and Redis)
        self._cache[cache_key] = (final_matches, time.time())
        
        # Also store in Redis if available
        if self.redis_cache:
            try:
                await self.redis_cache.set(cache_key, final_matches)
            except Exception as e:
                print(f"Failed to cache to Redis: {e}")
        
        # Determine overall confidence level
        if final_matches and final_matches[0].confidence >= 0.85:
            overall_confidence = ConfidenceLevel.HIGH
        elif final_matches and final_matches[0].confidence >= 0.5:
            overall_confidence = ConfidenceLevel.MEDIUM
        else:
            overall_confidence = ConfidenceLevel.LOW
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return SuggestionResponse(
            query=query,
            suggestions=final_matches,
            confidence_level=overall_confidence,
            message=self._get_message(final_matches),
            processing_time_ms=processing_time
        )
    
    def _rank_by_composite_score(self, matches: List[DiseaseMatch]) -> List[DiseaseMatch]:
        """
        Rank matches by composite score:
        0.4 × exact_match + 0.3 × semantic_similarity + 0.2 × target_count + 0.1 × ontology_trust
        """
        for match in matches:
            # Exact match bonus
            exact_bonus = 1.0 if match.match_type == MatchType.EXACT else 0.0
            
            # Semantic similarity (already in confidence for semantic matches)
            semantic_score = match.confidence
            
            # Target count score (log scale, max 1.0)
            if match.target_count > 0:
                target_score = min(1.0, math.log10(match.target_count + 1) / 3)
            else:
                target_score = 0.0
            
            # Ontology trust (EFO is trusted)
            ontology_trust = 1.0 if match.ontology_source == "EFO" else 0.8
            
            # Composite score
            composite = (
                0.4 * exact_bonus +
                0.3 * semantic_score +
                0.2 * target_score +
                0.1 * ontology_trust
            )
            
            # Update confidence with composite
            match.confidence = composite
            
            # Update confidence level
            if composite >= 0.7:
                match.confidence_level = ConfidenceLevel.HIGH
            elif composite >= 0.4:
                match.confidence_level = ConfidenceLevel.MEDIUM
            else:
                match.confidence_level = ConfidenceLevel.LOW
        
        # Sort by composite score
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        return matches
    
    def _get_message(self, matches: List[DiseaseMatch]) -> str:
        """Generate user-facing message based on match results"""
        if not matches:
            return "No diseases found. Try a different search term."
        
        top_match = matches[0]
        
        if top_match.match_type == MatchType.EXACT:
            return f"Found: {top_match.disease_name}"
        elif top_match.match_type == MatchType.TYPO_CORRECTED:
            return f"Did you mean: {top_match.disease_name}?"
        elif top_match.match_type == MatchType.HIERARCHICAL:
            return f"Showing broader category: {top_match.disease_name}"
        elif top_match.match_type == MatchType.FALLBACK:
            return "Here are some related diseases:"
        else:
            return f"Top match: {top_match.disease_name}"


# Singleton instance for reuse
_resolver_instance: Optional[DiseaseResolver] = None


def get_disease_resolver() -> DiseaseResolver:
    """Get or create the disease resolver singleton"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = DiseaseResolver()
    return _resolver_instance


# ==================== HOT DISEASE PRELOADING ====================

# Top 50 most commonly searched diseases for preloading
HOT_DISEASES: List[str] = [
    "Alzheimer's disease",
    "Parkinson's disease",
    "Type 2 diabetes",
    "Type 1 diabetes",
    "Breast cancer",
    "Lung cancer",
    "Colorectal cancer",
    "Prostate cancer",
    "Rheumatoid arthritis",
    "Multiple sclerosis",
    "Crohn's disease",
    "Ulcerative colitis",
    "Asthma",
    "COPD",
    "Depression",
    "Anxiety",
    "Schizophrenia",
    "Bipolar disorder",
    "Hypertension",
    "Heart failure",
    "Coronary artery disease",
    "Atrial fibrillation",
    "Stroke",
    "Epilepsy",
    "Migraine",
    "Psoriasis",
    "Eczema",
    "Lupus",
    "Osteoarthritis",
    "Osteoporosis",
    "Chronic kidney disease",
    "Hepatitis B",
    "Hepatitis C",
    "HIV/AIDS",
    "Tuberculosis",
    "Malaria",
    "Leukemia",
    "Lymphoma",
    "Melanoma",
    "Pancreatic cancer",
    "Ovarian cancer",
    "ALS",
    "Huntington's disease",
    "Cystic fibrosis",
    "Sickle cell disease",
    "Obesity",
    "NAFLD",
    "Cirrhosis",
    "Glioblastoma",
    "Macular degeneration",
]


async def preload_hot_diseases():
    """
    Preload commonly searched diseases into cache.
    Call this on application startup for faster initial responses.
    """
    resolver = get_disease_resolver()
    print(f"Preloading {len(HOT_DISEASES)} hot diseases into cache...")
    
    for disease in HOT_DISEASES:
        try:
            await resolver.resolve(disease, max_suggestions=5)
        except Exception as e:
            print(f"Failed to preload {disease}: {e}")
    
    print("Hot disease preloading complete.")


# ==================== REDIS CACHE INTEGRATION ====================

class RedisCacheAdapter:
    """
    Adapter to use Redis cache with the DiseaseResolver.
    Provides distributed caching for multi-instance deployments.
    """
    
    def __init__(self, cache_layer=None, prefix: str = "disease_resolver:"):
        self.cache_layer = cache_layer
        self.prefix = prefix
        self.ttl = 3600  # 1 hour
    
    async def get(self, key: str) -> Optional[List[DiseaseMatch]]:
        """Get cached disease matches from Redis"""
        if not self.cache_layer:
            return None
        
        try:
            data = await self.cache_layer.get(f"{self.prefix}{key}")
            if data:
                # Deserialize from dict list
                matches = []
                for d in data:
                    matches.append(DiseaseMatch(
                        disease_id=d.get("disease_id", ""),
                        disease_name=d.get("disease_name", ""),
                        match_type=MatchType(d.get("match_type", "exact")),
                        confidence=d.get("confidence", 0.0),
                        confidence_level=ConfidenceLevel(d.get("confidence_level", "low")),
                        target_count=d.get("target_count", 0),
                        synonyms=d.get("synonyms", []),
                        description=d.get("description", ""),
                        ontology_source=d.get("ontology_source", "EFO"),
                        original_query=d.get("original_query", ""),
                        correction_applied=d.get("correction_applied", ""),
                        parent_diseases=d.get("parent_diseases", [])
                    ))
                return matches
        except Exception as e:
            print(f"Redis cache get error: {e}")
        
        return None
    
    async def set(self, key: str, matches: List[DiseaseMatch]):
        """Cache disease matches to Redis"""
        if not self.cache_layer or not matches:
            return
        
        try:
            # Serialize to dict list
            data = [
                {
                    "disease_id": m.disease_id,
                    "disease_name": m.disease_name,
                    "match_type": m.match_type.value,
                    "confidence": m.confidence,
                    "confidence_level": m.confidence_level.value,
                    "target_count": m.target_count,
                    "synonyms": m.synonyms,
                    "description": m.description,
                    "ontology_source": m.ontology_source,
                    "original_query": m.original_query,
                    "correction_applied": m.correction_applied,
                    "parent_diseases": m.parent_diseases
                }
                for m in matches
            ]
            await self.cache_layer.set(f"{self.prefix}{key}", data, ttl=self.ttl)
        except Exception as e:
            print(f"Redis cache set error: {e}")


def configure_redis_cache(cache_layer):
    """
    Configure the disease resolver to use Redis caching.
    Call this on application startup after Redis is initialized.
    
    Example:
        from app.cache import CacheLayer
        from app.disease_resolver import configure_redis_cache
        
        cache = CacheLayer()
        configure_redis_cache(cache)
    """
    resolver = get_disease_resolver()
    resolver.redis_cache = RedisCacheAdapter(cache_layer)
    print("Disease resolver configured with Redis cache")

