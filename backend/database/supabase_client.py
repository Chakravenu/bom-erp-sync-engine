import logging
from typing import List, Dict, Optional
from supabase import create_client
from config import Config
from models.bom_models import BOMPart, BOMVersion

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for S1000D BOM database in Supabase with multi level support"""
    
    def __init__(self):
        self.client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        logger.info("Supabase client initialized")
    
    def get_assemblies(self) -> List[Dict]:
        """Fetch all assemblies"""
        result = self.client.table("bom_assemblies")\
            .select("*")\
            .order("bom_level")\
            .execute()
        
        return result.data
    
    def get_components(self, assembly_id: str) -> List[Dict]:
        """Fetch all components for a specific assembly"""
        result = self.client.table("bom_components")\
            .select("*")\
            .eq("assembly_id", assembly_id)\
            .execute()
        return result.data
    
    def build_bom_tree(self, version_id: Optional[int] = None) -> List[BOMPart]:
        """
        Build complete hierarchical BOM tree
        Returns tree structure with all levels
        """
        assemblies = self.get_assemblies() or []
        
        # Create lookup map
        assembly_map = {a.get("id"): a for a in assemblies}
        
        # Build tree recursively
        root_assemblies = []
        
        for assembly in assemblies:
            if assembly.get("parent_assembly_id") is None:
                # This is a root (Level 0) assembly
                tree = self._build_subtree(assembly, assembly_map)
                root_assemblies.append(tree)
        
        logger.info(f"Built BOM tree with {len(root_assemblies)} root assemblies")
        return root_assemblies
    
    def _build_subtree(self, assembly: Dict, assembly_map: Dict) -> BOMPart:
        """Recursively build subtree for an assembly"""
        node = BOMPart(
            id=assembly["id"],
            part_number=assembly["part_number"],
            description=assembly["description"],
            category=assembly.get("category"),
            quantity=assembly.get("quantity", 1),
            bom_level=assembly.get("bom_level", 0),
            is_assembly=True,
            unit_price=0.0  # Will be calculated from children
        )
        
        # Get child assemblies
        child_assemblies = [
            a for a in assembly_map.values() 
            if a["parent_assembly_id"] == assembly["id"]
        ]
        
        # Get leaf components
        components = self.get_components(assembly["id"]) or []
        
        # Add child assemblies recursively
        for child_asm in child_assemblies:
            child_tree = self._build_subtree(child_asm, assembly_map)
            node.children.append(child_tree)
            node.unit_price += child_tree.unit_price * child_tree.quantity
        
        # Add leaf components
        for comp in components:
            leaf = BOMPart(
                id=comp.get("id"),
                part_number=comp.get("part_number"),
                description=comp.get("description"),
                quantity=comp.get("quantity", 1),
                unit_price=float(comp.get("unit_price") or 0.0),
                bom_level=node.bom_level + 1,
                parent_assembly=assembly.get("part_number"),
                is_assembly=False,
                supplier=comp.get("supplier")
            )
            node.children.append(leaf)
            node.unit_price += leaf.unit_price * leaf.quantity
        
        return node
    
    def flatten_bom(self, version_id: Optional[int] = None) -> List[BOMPart]:
        """
        Flatten hierarchical BOM into single list
        Used for ETL operations
        """
        tree = self.build_bom_tree(version_id)
        flattened = []
        
        def traverse(node: BOMPart, parent: Optional[str] = None):
            node.parent_assembly = parent
            flattened.append(node)
            
            for child in node.children:
                traverse(child, node.part_number)
        
        for root in tree:
            traverse(root)
        
        logger.info(f"Flattened BOM: {len(flattened)} total parts")
        return flattened
    
    def get_bom_statistics(self, version_id: Optional[int] = None) -> Dict:
        """Get summary statistics for BOM"""
        tree = self.build_bom_tree(version_id)
        
        total_parts = 0
        total_cost = 0.0
        assemblies_count = 0
        components_count = 0
        max_depth = 0
        
        def count(node: BOMPart, depth: int):
            nonlocal total_parts, total_cost, assemblies_count, components_count, max_depth
            total_parts += 1
            max_depth = max(max_depth, depth)
            
            if node.is_assembly:
                assemblies_count += 1
            else:
                components_count += 1
                total_cost += node.unit_price * node.quantity
            
            for child in node.children:
                count(child, depth + 1)
        
        for root in tree:
            count(root, 0)
        
        return {
            "total_parts": total_parts,
            "assemblies": assemblies_count,
            "components": components_count,
            "total_cost": round(total_cost, 2),
            "max_depth": max_depth
        }