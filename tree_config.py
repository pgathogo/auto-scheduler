# Create a recursive function that reads the tree.txt file and builds a tree of nodes.
# the format of th file is as follows:
# id|node_name|parent_id

# The tree is built in the form of a dictionary where the key is the node name and the value is a list of children nodes.
# The tree  should be rendered in the QTreeView widget. The tree should be built in the following way:

# 1. Read the tree.txt file and build a dictionary of nodes.

class Node:
    def __init__(self, name):
        self.node_id = -1
        self.parent_id = -1
        self.name = name
        self.children = []

    def add_child(self, child):
        self.children.append(child)


class TreeConfig:
    def __init__(self, records: list[tuple]):
        self.records = records

    def read_tree_file(self):
        tree = []
        l = len(tree)
        with open(self.tree_file, 'r') as f:
            for line in f:
                id, node_name, parent_id = line.strip().split('|')

                print(f"{id} {node_name} {parent_id}")

                node = Node(node_name)
                node.name = node_name
                node.node_id = int(id)
                node.parent_id = int(parent_id)
                node.children = []

                tree = self.grow_tree(node, tree)

        return tree

    def make_tree(self):
        tree = []
        for record in self.records:
            node = Node(record[1])
            node.node_id = int(record[0])
            node.parent_id = int(record[2])
            node.children = []

            tree = self.grow_tree(node, tree)

        return tree
        

    def grow_tree(self, new_node, tree ):
        if len(tree) == 0:
            tree.append(new_node)
            return tree
            
        for node in tree:
            if new_node.parent_id == node.node_id:
                node.children.append(new_node)
            else:
                if len(node.children) == 0:
                    continue
                else:
                    self.grow_tree(new_node, node.children)
        return tree

    def print_tree(self, tree, indent=0):
        for node in tree:
            print(" " * indent, end="")
            print(f"{node.name}")
            self.print_tree(node.children, indent=indent + 2)

if __name__ == "__main__":
    print("Building tree...")
    tc = TreeConfig('data/tree.txt')
    tree = tc.read_tree_file()
    tc.print_tree(tree)
    