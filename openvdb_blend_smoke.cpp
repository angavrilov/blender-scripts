#include <iostream>
#include <stdlib.h>

#include <openvdb/openvdb.h>

using namespace std;

using openvdb::MetaMap;
using openvdb::GridBase;
using openvdb::CombineArgs;

using openvdb::Vec3i;
using openvdb::Vec3s;
using openvdb::FloatGrid;
using openvdb::Vec3SGrid;

template<class T>
bool verify_metadata_match(MetaMap::Ptr metadata1, MetaMap::Ptr metadata2, const char *name)
{
    try {
        T val1 = metadata1->metaValue<T>(name);
        T val2 = metadata2->metaValue<T>(name);

        if (val1 == val2)
            return true;

        cerr << "Mismatch in " << name << endl;
    }
    catch (openvdb::TypeError&) {
        cerr << "Wrong type of " << name << endl;
    }
    catch (openvdb::Exception&) {
        cerr << "Error retrieving " << name << endl;
    }

    return false;
}

#if 0
template<class T>
struct BlendOp {
    float factor;

    BlendOp(float factor) : factor(factor) {}

    void operator() (CombineArgs<T>& args) const {
        T aval = args.aIsActive() ? args.a() : T();
        T bval = args.bIsActive() ? args.b() : T();
        args.setResult(aval * (1.0f - factor) + bval * factor);
        args.setResultIsActive(args.aIsActive() || args.bIsActive());
    }
};
#endif

template<class GRID>
void blend_grids(GridBase::Ptr pgrid1, GridBase::Ptr pgrid2, float coeff)
{
    typename GRID::Ptr grid1 = openvdb::gridPtrCast<GRID>(pgrid1);
    typename GRID::Ptr grid2 = openvdb::gridPtrCast<GRID>(pgrid2);

    if (!grid1 || !grid2)
        return;

#if 0
    typename GRID::TreeType &tree1 = grid1->tree();
    typename GRID::TreeType &tree2 = grid2->tree();

    tree1.combineExtended(tree2, BlendOp<typename GRID::ValueType>(coeff));
#else
    typename GRID::ConstAccessor acc2 = grid2->getConstAccessor();

    for (typename GRID::ValueOnIter iter = grid1->beginValueOn(); iter; ++iter) {
        if (!iter.isVoxelValue())
            continue;

        typename GRID::ValueType a = iter.getValue(), b = acc2.getValue(iter.getCoord());

        iter.setValue(a * (1.0f - coeff) + b * coeff);
    }

    typename GRID::Accessor acc1 = grid1->getAccessor();

    for (typename GRID::ValueOnIter iter = grid2->beginValueOn(); iter; ++iter) {
        if (!iter.isVoxelValue())
            continue;

        if (!acc1.isValueOn(iter.getCoord()))
            acc1.setValueOn(iter.getCoord(), iter.getValue() * coeff);
    }

    grid1->addStatsMetadata();
#endif
}

int main(int argc, const char *argv[])
{
    openvdb::initialize();

    if (argc < 1+3+1) {
        cerr << "Usage: openvdb_blend_smoke <outfile> <infile1> <infile2> <coeff>" << endl;
        return 1;
    }

    const char *fn_out = argv[1];
    const char *fn_in1 = argv[2];
    const char *fn_in2 = argv[3];
    float coeff = (float)atof(argv[4]);

    /* Open input files */
    openvdb::io::File infile1(fn_in1);
    openvdb::io::File infile2(fn_in2);

    try {
        infile1.open();
    } catch (openvdb::IoError&) {
        cerr << "Could not open " << fn_in1 << endl;
        return 1;
    }

    try {
        infile2.open();
    } catch (openvdb::IoError&) {
        cerr << "Could not open " << fn_in2 << endl;
        return 1;
    }

    /* Check metadata */
    MetaMap::Ptr metadata1 = infile1.getMetadata();
    MetaMap::Ptr metadata2 = infile2.getMetadata();

    if (!verify_metadata_match<Vec3i>(metadata1, metadata2, "blender/smoke/resolution"))
        return 1;
    if (!verify_metadata_match<Vec3i>(metadata1, metadata2, "blender/smoke/shift"))
        return 1;
    if (!verify_metadata_match<int>(metadata1, metadata2, "blender/smoke/fluid_fields"))
        return 1;
    if (!verify_metadata_match<int>(metadata1, metadata2, "blender/smoke/active_fields"))
        return 1;

    /* Read grids */
    openvdb::GridPtrVecPtr grids = infile1.getGrids();

    for (unsigned i = 0; i < grids->size(); i++)
    {
        openvdb::GridBase::Ptr grid1 = (*grids)[i];

        if (!infile2.hasGrid(grid1->getName())) {
            cerr << "Cannot find second grid " << grid1->getName() << endl;
            return 1;
        }

        openvdb::GridBase::Ptr grid2 = infile2.readGrid(grid1->getName());

        if (grid1->isType<FloatGrid>()) {
            blend_grids<FloatGrid>(grid1, grid2, coeff);
        }
        else if (grid1->isType<Vec3SGrid>()) {
            blend_grids<Vec3SGrid>(grid1, grid2, coeff);
        }
    }

    /* Write output */
    openvdb::io::File outfile(fn_out);

    outfile.write(*grids, *metadata1);
    outfile.close();

    return 0;
}
