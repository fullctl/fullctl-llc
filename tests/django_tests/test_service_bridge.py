import fullctl.service_bridge.aaactl as aaactl


def test_aaactl_federated_service_url(settings):
    """
    Tests that the aaactl federated service url is correct
    """

    # temporarily override aaactl url to test://aaactl
    # making it use mock data
    settings.AAACTL_URL = "test://aaactl"

    results = [
        aaactl.FederatedServiceURL().federated_services(
            ["peerctl"],
            lambda source_id: source_id.replace(":", "."),
            ["ix.pdbctl:1", "ix.ixctl:1"],
        )
    ]

    assert len(results) == 1
    assert results[0]["peerctl"]["ix.pdbctl:1"].service_slug == "peerctl"
    assert results[0]["peerctl"]["ix.pdbctl:1"].url == "https://peerctl.example.com"
    assert list(results[0].keys()) == ["peerctl"]
