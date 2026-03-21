declare module 'react-force-graph-2d' {
    import * as React from 'react';

    export interface ForceGraphMethods {
        zoomToFit?: (durationMs?: number, padding?: number, nodeFilter?: (node: unknown) => boolean) => void;
    }

    const ForceGraph2D: React.ForwardRefExoticComponent<Record<string, unknown> & React.RefAttributes<ForceGraphMethods>>;

    export default ForceGraph2D;
}
