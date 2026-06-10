"""Core graph data structure."""


class Graph:
    """A simple graph implementation using adjacency lists."""

    def __init__(self):
        self.adjacency_list = {}

    def add_vertex(self, vertex):
        """Add a vertex to the graph."""
        if vertex not in self.adjacency_list:
            self.adjacency_list[vertex] = []

    def add_edge(self, vertex1, vertex2, weight=1):
        """Add an edge between two vertices."""
        if vertex1 not in self.adjacency_list:
            self.add_vertex(vertex1)
        if vertex2 not in self.adjacency_list:
            self.add_vertex(vertex2)
        self.adjacency_list[vertex1].append((vertex2, weight))

    def get_neighbors(self, vertex):
        """Get neighbors of a vertex."""
        return self.adjacency_list.get(vertex, [])
