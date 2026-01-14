#!/bin/bash
# Quick diagnostic script to check CML environment setup

echo "🔍 Checking CML Environment Setup"
echo "=================================="
echo ""

# Check required environment variables
echo "📋 Required Environment Variables:"
if [ -z "$CML_HOST" ]; then
    echo "  ❌ CML_HOST not set"
else
    echo "  ✅ CML_HOST: $CML_HOST"
fi

if [ -z "$CML_API_KEY" ]; then
    echo "  ❌ CML_API_KEY not set"
else
    echo "  ✅ CML_API_KEY: (set, length: ${#CML_API_KEY})"
fi

echo ""
echo "📋 Optional Environment Variables:"
if [ -z "$GITHUB_REPOSITORY" ]; then
    echo "  ⚠️  GITHUB_REPOSITORY not set (optional)"
else
    echo "  ✅ GITHUB_REPOSITORY: $GITHUB_REPOSITORY"
fi

if [ -z "$GH_PAT" ]; then
    echo "  ⚠️  GH_PAT not set (optional)"
else
    echo "  ✅ GH_PAT: (set, length: ${#GH_PAT})"
fi

echo ""
echo "🌐 Network Connectivity:"

# Test connection to CML host
if [ -n "$CML_HOST" ]; then
    HOST=$(echo $CML_HOST | sed 's|https://||; s|http://||; s|/.*||')
    if timeout 5 bash -c "echo > /dev/tcp/$HOST/443" 2>/dev/null; then
        echo "  ✅ Can reach $HOST (port 443)"
    else
        echo "  ❌ Cannot reach $HOST (port 443)"
        echo "     Check: firewall, VPN, CML_HOST value"
    fi
else
    echo "  ⚠️  Cannot test - CML_HOST not set"
fi

echo ""
echo "📝 Setup Instructions:"
echo ""
echo "If you see ❌ marks above, run:"
echo ""
echo "  export CML_HOST='https://your-cml-instance.cloudera.site'"
echo "  export CML_API_KEY='your-api-key-here'"
echo "  export GITHUB_REPOSITORY='your-org/your-repo'  # Optional, for git integration"
echo "  export GH_PAT='your-github-token'               # Optional, for git integration"
echo ""
echo "Then run the test:"
echo "  python cai_integration/local_test/test_project_creation.py"
echo ""
