"""
Test script for SIGMA Phase 2: Git Integration

Tests the ingest_project MCP tool with the current repository.
"""

import asyncio
import json
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set test-specific environment variables (use .env for sensitive values)
os.environ["GIT_INTEGRATION_ENABLED"] = "true"
os.environ["GRAPHITI_ENABLED"] = "true"

# Import git integration utilities
from src.openmemory.app.utils.git_integration import GitProjectAnalyzer, is_git_integration_enabled


def test_git_integration_availability():
    """Test if git integration is available and enabled."""
    print("\n" + "="*80)
    print("Test 1: Git Integration Availability")
    print("="*80)
    
    enabled = is_git_integration_enabled()
    print(f"✓ GIT_INTEGRATION_ENABLED: {enabled}")
    
    if not enabled:
        print("⚠️  Git integration is disabled. Set GIT_INTEGRATION_ENABLED=true")
        return False
    
    return True


def test_analyze_current_repository():
    """Test analyzing the current repository (mcp-memory-server-sigma)."""
    print("\n" + "="*80)
    print("Test 2: Analyze Current Repository")
    print("="*80)
    
    # Get current repository path
    repo_path = Path(__file__).parent
    print(f"Repository path: {repo_path}")
    
    try:
        # Initialize analyzer
        analyzer = GitProjectAnalyzer(str(repo_path))
        print("✓ GitProjectAnalyzer initialized")
        
        # Get repository info
        repo_info = analyzer.get_repository_info()
        print(f"\n📁 Repository: {repo_info['name']}")
        print(f"   Active Branch: {repo_info['active_branch']}")
        print(f"   Branches: {', '.join(repo_info['branches'][:5])}")
        print(f"   Is Dirty: {repo_info['is_dirty']}")
        
        # Get recent commits
        commits = analyzer.get_recent_commits(limit=10)
        print(f"\n📝 Recent Commits: {len(commits)}")
        for commit in commits[:3]:
            print(f"   - {commit['short_hash']}: {commit['message'][:60]}")
        
        # Analyze commit patterns
        patterns = analyzer.analyze_commit_patterns(commits)
        print(f"\n📊 Commit Patterns:")
        print(f"   Total Commits Analyzed: {patterns['total_commits']}")
        print(f"   Contributors: {', '.join(patterns['authors'][:5])}")
        print(f"   Commit Types: {patterns['commit_types']}")
        if patterns.get('decision_keywords'):
            print(f"   Decision Keywords Found: {len(patterns['decision_keywords'])}")
            for kw in patterns['decision_keywords'][:3]:
                print(f"      - {kw['keyword']}: {kw['commit']} - {kw['message'][:50]}")
        
        # Detect dependencies
        dependencies = analyzer.detect_dependencies()
        print(f"\n📦 Dependencies:")
        for ecosystem, deps in dependencies.items():
            print(f"   {ecosystem.title()}: {len(deps)} packages")
            for dep in deps[:5]:
                print(f"      - {dep['name']} {dep.get('version', '')}")
        
        # Extract file structure
        file_structure = analyzer.extract_file_structure(max_depth=2)
        print(f"\n📂 File Structure:")
        print(f"   Total Files: {file_structure['total_files']}")
        print(f"   Languages: {file_structure['languages']}")
        
        print("\n✓ Repository analysis completed successfully")
        return True
        
    except Exception as e:
        print(f"\n✗ Error analyzing repository: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_project_analysis():
    """Test complete project analysis."""
    print("\n" + "="*80)
    print("Test 3: Full Project Analysis")
    print("="*80)
    
    repo_path = Path(__file__).parent
    
    try:
        analyzer = GitProjectAnalyzer(str(repo_path))
        analysis = analyzer.analyze_full_project(commit_limit=20)
        
        print(f"\n📊 Analysis Summary:")
        print(f"   Project: {analysis['repository']['name']}")
        print(f"   Analyzed At: {analysis['analyzed_at']}")
        print(f"   Total Commits: {analysis['commits']['total_analyzed']}")
        print(f"   Languages: {list(analysis['file_structure']['languages'].keys())}")
        print(f"   Dependencies: {list(analysis['dependencies'].keys())}")
        
        # Save to file for inspection
        output_file = Path(__file__).parent / "test_git_analysis_output.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n✓ Full analysis saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error in full analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all git integration tests."""
    print("\n" + "="*80)
    print("🧪 SIGMA Phase 2: Git Integration Tests")
    print("="*80)
    
    results = []
    
    # Test 1: Availability
    results.append(("Git Integration Availability", test_git_integration_availability()))
    
    if results[0][1]:  # Only proceed if git integration is available
        # Test 2: Repository analysis
        results.append(("Analyze Current Repository", test_analyze_current_repository()))
        
        # Test 3: Full project analysis
        results.append(("Full Project Analysis", test_full_project_analysis()))
    
    # Print summary
    print("\n" + "="*80)
    print("📊 Test Summary")
    print("="*80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("="*80)
    
    return all(passed for _, passed in results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
