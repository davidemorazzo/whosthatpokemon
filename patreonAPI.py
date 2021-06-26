import patreon

#Versione API:2
# ID_CLIENT = "FvvDJpIOSPHsLycGZa3pJvdfywCgXfsHKE22kG09Tu1GvRoYNuDIy2cmTHTyOeig"
# CLIENT_SECRET = "S2uayKapJXy8Yw2Sox388ClTV1wJ9XX30HKH9M_mVyDGEyN1C14ow5PxtueauwcC"
# ACCESS_TOKEN = "pskTwhilaLvThYGConYs0go1J_s7BrcyCDqX3xdn9bw"
# UPDATE_TOKEN = "Hsu_Oa5QDXvw_lOo7OU5wDuG2diIsqWLXEnPq03hFho"
# CREATOR_ID = "57231174"

def fetch_patreons(ACCESS_TOKEN) -> dict:
    api_client = patreon.API(ACCESS_TOKEN)

    # Get the campaign ID
    campaign_response = api_client.fetch_campaign()
    campaign_id = campaign_response.data()[0].id()

    # Fetch all pledges
    all_pledges = []
    cursor = None
    while True:
        pledges_response = api_client.fetch_page_of_pledges(campaign_id, 25, cursor=cursor)
        all_pledges.append(pledges_response.data())
        cursor = api_client.extract_cursor(pledges_response)
        if not cursor:
            break
    # FINO A QUI PRESO DAI DOCS
    
    ## => LIST OF ACTIVE USERS
    active_user_dict = {}
    for pledge in all_pledges:
        data = pledge.data()
        valid = data.attribute('declined_since')
        member = data.relationship('patron')
        discord_id = member.attribute('discord_id')
        rewards = []
        for r in member.relationship('reward'):
            rewards.append(r.data().id())

        active_user_dict[discord_id] = [valid, rewards]
    
    return active_user_dict
