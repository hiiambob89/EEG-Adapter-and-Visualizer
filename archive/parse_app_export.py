#!/usr/bin/env python3
"""
Parse and visualize Serenibrain app export data

The app exports 3 sections:
1. Raw brainwave voltages with decomposed frequency bands
2. Real-time scores over time
3. Session summary with statistics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import os


class SerenibrainExport:
    """Parse and analyze Serenibrain app export CSV/TSV data"""
    
    def __init__(self, file_path):
        """Load and parse the export file"""
        self.file_path = file_path
        self.raw_brainwaves = None
        self.scores = None
        self.session_summary = None
        
        self._parse_file()
    
    def _parse_file(self):
        """Parse the multi-section export file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by double newlines (sections)
        sections = content.strip().split('\n\n')
        
        # Parse each section
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.strip().split('\n')
            header = lines[0]
            
            # Section 1: Raw Brainwaves
            if 'Raw Brainwaves Voltage' in header:
                self._parse_brainwaves(lines)
            
            # Section 2: Real-time Scores
            elif 'Real-time Score' in header:
                self._parse_scores(lines)
            
            # Section 3: Session Summary
            elif 'Practice Name' in header:
                self._parse_summary(lines)
    
    def _parse_brainwaves(self, lines):
        """Parse brainwave voltage data"""
        from io import StringIO
        data = '\n'.join(lines)
        self.raw_brainwaves = pd.read_csv(StringIO(data), sep='\t')
        
        # Convert timestamp to seconds
        self.raw_brainwaves['Time (s)'] = self.raw_brainwaves['Practice Timestamp (ms)'] / 1000.0
    
    def _parse_scores(self, lines):
        """Parse real-time score data"""
        from io import StringIO
        data = '\n'.join(lines)
        self.scores = pd.read_csv(StringIO(data), sep='\t')
        
        # Convert timestamp to seconds
        self.scores['Time (s)'] = self.scores['Practice Timestamp (ms)'] / 1000.0
    
    def _parse_summary(self, lines):
        """Parse session summary"""
        from io import StringIO
        data = '\n'.join(lines)
        self.session_summary = pd.read_csv(StringIO(data), sep='\t')
    
    def get_band_columns(self):
        """Get list of brainwave band columns"""
        if self.raw_brainwaves is None:
            return []
        
        bands = []
        for col in self.raw_brainwaves.columns:
            if 'Brainwave Voltage' in col and 'Raw' not in col:
                # Extract band name (e.g., "Delta" from "Delta Brainwave Voltage(µV)")
                band = col.split(' ')[0]
                bands.append(band)
        return bands
    
    def plot_timeseries(self, output_dir='plots'):
        """Plot all brainwave timeseries"""
        if self.raw_brainwaves is None:
            print("No brainwave data to plot")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get time and band data
        time = self.raw_brainwaves['Time (s)'].values
        bands = self.get_band_columns()
        
        # Create subplot for each band + raw
        fig, axes = plt.subplots(len(bands) + 1, 1, figsize=(14, 3*(len(bands)+1)), sharex=True)
        
        # Plot raw signal
        raw_voltage = self.raw_brainwaves['Raw Brainwaves Voltage(µV)'].values
        axes[0].plot(time, raw_voltage, 'k-', linewidth=0.5)
        axes[0].set_ylabel('Raw (µV)', fontsize=10)
        axes[0].set_title('Raw EEG Signal', fontsize=12, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        
        # Plot each frequency band
        colors = ['purple', 'blue', 'green', 'orange', 'red', 'brown', 'pink']
        for i, band in enumerate(bands):
            col_name = f'{band} Brainwave Voltage(µV)'
            if col_name in self.raw_brainwaves.columns:
                data = self.raw_brainwaves[col_name].values
                axes[i+1].plot(time, data, color=colors[i % len(colors)], linewidth=1)
                axes[i+1].set_ylabel(f'{band} (µV)', fontsize=10)
                axes[i+1].set_title(f'{band} Band', fontsize=12, fontweight='bold')
                axes[i+1].grid(True, alpha=0.3)
                axes[i+1].axhline(0, color='gray', linestyle='--', alpha=0.5)
        
        axes[-1].set_xlabel('Time (s)', fontsize=12)
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, 'app_export_brainwaves.png')
        plt.savefig(output_path, dpi=150)
        print(f"Saved brainwave plot: {output_path}")
        plt.close()
    
    def plot_scores(self, output_dir='plots'):
        """Plot real-time scores"""
        if self.scores is None:
            print("No score data to plot")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        fig, ax = plt.subplots(figsize=(12, 4))
        
        time = self.scores['Time (s)'].values
        score = self.scores['Real-time Score'].values
        
        ax.plot(time, score, 'b-', linewidth=2, marker='o', markersize=3)
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel('Score', fontsize=12)
        ax.set_title('Real-time Meditation Score', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, max(score) * 1.1])
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, 'app_export_scores.png')
        plt.savefig(output_path, dpi=150)
        print(f"Saved score plot: {output_path}")
        plt.close()
    
    def plot_band_powers(self, output_dir='plots'):
        """Plot band power distribution over time"""
        if self.raw_brainwaves is None:
            print("No brainwave data to plot")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        bands = self.get_band_columns()
        time = self.raw_brainwaves['Time (s)'].values
        
        # Calculate absolute power for each band
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
        
        # Top: Stacked area plot of band powers
        band_data = []
        labels = []
        colors = ['purple', 'blue', 'green', 'orange', 'red', 'brown', 'pink']
        
        for band in bands:
            col_name = f'{band} Brainwave Voltage(µV)'
            if col_name in self.raw_brainwaves.columns:
                # Use absolute value for power representation
                data = np.abs(self.raw_brainwaves[col_name].values)
                band_data.append(data)
                labels.append(band)
        
        band_data = np.array(band_data)
        ax1.stackplot(time, *band_data, labels=labels, colors=colors[:len(labels)], alpha=0.7)
        ax1.set_ylabel('Absolute Voltage (µV)', fontsize=12)
        ax1.set_title('Band Power Distribution (Stacked)', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right', fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Bottom: Individual band powers
        for i, band in enumerate(labels):
            ax2.plot(time, band_data[i], label=band, color=colors[i], linewidth=1.5, alpha=0.8)
        
        ax2.set_xlabel('Time (s)', fontsize=12)
        ax2.set_ylabel('Absolute Voltage (µV)', fontsize=12)
        ax2.set_title('Individual Band Powers', fontsize=14, fontweight='bold')
        ax2.legend(loc='upper right', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, 'app_export_band_powers.png')
        plt.savefig(output_path, dpi=150)
        print(f"Saved band power plot: {output_path}")
        plt.close()
    
    def plot_session_summary(self, output_dir='plots'):
        """Plot session summary statistics"""
        if self.session_summary is None:
            print("No session summary to plot")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        row = self.session_summary.iloc[0]
        
        fig = plt.figure(figsize=(14, 6))
        
        # Left: State proportions pie chart
        ax1 = plt.subplot(1, 3, 1)
        states = ['Calm', 'Relaxed', 'Active']
        proportions = [
            float(row['Calm State Proportion'].rstrip('%')),
            float(row['Relaxed State Proportion'].rstrip('%')),
            float(row['Active State Proportion'].rstrip('%'))
        ]
        colors = ['blue', 'green', 'red']
        ax1.pie(proportions, labels=states, autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('Mental State Distribution', fontsize=12, fontweight='bold')
        
        # Middle: Band proportion (if available)
        ax2 = plt.subplot(1, 3, 2)
        if 'Delta Brainwave Proportion' in row:
            # For now just show delta, could expand if more bands are in summary
            ax2.bar(['Delta'], [float(row['Delta Brainwave Proportion'].rstrip('%'))], color='purple')
            ax2.set_ylabel('Proportion (%)', fontsize=10)
            ax2.set_title('Brainwave Band Proportion', fontsize=12, fontweight='bold')
            ax2.set_ylim([0, 100])
        
        # Right: Summary stats as text
        ax3 = plt.subplot(1, 3, 3)
        ax3.axis('off')
        
        summary_text = f"""
Session Summary
{'='*40}

Practice: {row['Practice Name']}
Mode: {row['Practice Mode']}
Difficulty: {row['Practice Difficulty']}

Duration: {row['Practice Duration (s)']} seconds
Average Score: {row['Average Score']}
Evaluation: {row['Practice Evaluation']}

State Durations:
  Calm: {int(proportions[0]/100 * row['Practice Duration (s)'])} s
  Relaxed: {int(proportions[1]/100 * row['Practice Duration (s)'])} s
  Active: {int(proportions[2]/100 * row['Practice Duration (s)'])} s
"""
        ax3.text(0.1, 0.5, summary_text, fontsize=10, family='monospace', 
                verticalalignment='center')
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, 'app_export_summary.png')
        plt.savefig(output_path, dpi=150)
        print(f"Saved summary plot: {output_path}")
        plt.close()
    
    def print_summary(self):
        """Print summary statistics"""
        print("\n" + "="*70)
        print("SERENIBRAIN APP EXPORT SUMMARY")
        print("="*70)
        
        if self.raw_brainwaves is not None:
            print(f"\nBrainwave Data:")
            print(f"  Samples: {len(self.raw_brainwaves)}")
            print(f"  Duration: {self.raw_brainwaves['Time (s)'].max():.1f} seconds")
            print(f"  Bands: {', '.join(self.get_band_columns())}")
            
            # Stats for each band
            print(f"\n  Band Statistics (µV):")
            for band in self.get_band_columns():
                col = f'{band} Brainwave Voltage(µV)'
                if col in self.raw_brainwaves.columns:
                    data = self.raw_brainwaves[col].values
                    print(f"    {band:8s}: mean={np.mean(data):8.2f}, "
                          f"std={np.std(data):8.2f}, "
                          f"range=[{np.min(data):8.2f}, {np.max(data):8.2f}]")
        
        if self.scores is not None:
            print(f"\nScore Data:")
            print(f"  Samples: {len(self.scores)}")
            print(f"  Duration: {self.scores['Time (s)'].max():.1f} seconds")
            print(f"  Score range: {self.scores['Real-time Score'].min():.0f} - "
                  f"{self.scores['Real-time Score'].max():.0f}")
            print(f"  Average score: {self.scores['Real-time Score'].mean():.1f}")
        
        if self.session_summary is not None:
            print(f"\nSession Summary:")
            row = self.session_summary.iloc[0]
            print(f"  Practice: {row['Practice Name']}")
            print(f"  Begin Time: {row['Practice Begin Time']}")
            print(f"  Duration: {row['Practice Duration (s)']} seconds")
            print(f"  Average Score: {row['Average Score']}")
            print(f"  Evaluation: {row['Practice Evaluation']}")
            print(f"  State Proportions:")
            print(f"    Calm: {row['Calm State Proportion']}")
            print(f"    Relaxed: {row['Relaxed State Proportion']}")
            print(f"    Active: {row['Active State Proportion']}")
        
        print("="*70 + "\n")
    
    def export_to_csv(self, output_dir='exports'):
        """Export parsed data to separate CSV files"""
        os.makedirs(output_dir, exist_ok=True)
        
        if self.raw_brainwaves is not None:
            path = os.path.join(output_dir, 'brainwaves.csv')
            self.raw_brainwaves.to_csv(path, index=False)
            print(f"Exported brainwaves: {path}")
        
        if self.scores is not None:
            path = os.path.join(output_dir, 'scores.csv')
            self.scores.to_csv(path, index=False)
            print(f"Exported scores: {path}")
        
        if self.session_summary is not None:
            path = os.path.join(output_dir, 'summary.csv')
            self.session_summary.to_csv(path, index=False)
            print(f"Exported summary: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse and visualize Serenibrain app export data"
    )
    parser.add_argument('file', help='Path to app export file')
    parser.add_argument('--output-dir', '-o', default='plots',
                       help='Output directory for plots (default: plots)')
    parser.add_argument('--export-csv', action='store_true',
                       help='Export parsed data to CSV files')
    parser.add_argument('--no-plots', action='store_true',
                       help='Skip generating plots')
    
    args = parser.parse_args()
    
    # Parse the export file
    print(f"\nParsing: {args.file}")
    export = SerenibrainExport(args.file)
    
    # Print summary
    export.print_summary()
    
    # Generate plots
    if not args.no_plots:
        print(f"\nGenerating plots to {args.output_dir}/")
        export.plot_timeseries(args.output_dir)
        export.plot_scores(args.output_dir)
        export.plot_band_powers(args.output_dir)
        export.plot_session_summary(args.output_dir)
    
    # Export CSV if requested
    if args.export_csv:
        export.export_to_csv()


if __name__ == '__main__':
    main()
